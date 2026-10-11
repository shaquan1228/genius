#!/usr/bin/env python3
"""Run paired baseline/Genius trials using a JSON subprocess adapter."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shlex
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
IGNORED = {".git", "__pycache__"}


def snapshot(root):
    files = {}
    for path in sorted(root.rglob("*")):
        if IGNORED.intersection(path.relative_to(root).parts):
            continue
        if path.is_symlink():
            files[path.relative_to(root).as_posix()] = "link:" + os.readlink(path)
        elif path.is_file():
            files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def execute(command, cwd, stdin, timeout):
    """Kill the process group on timeout, including an adapter's agent child."""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, env=env, start_new_session=True)
    try:
        stdout, stderr = process.communicate(stdin, timeout=timeout)
        return process.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr, True


def initialise_repo(workspace):
    for args in [["init", "-q", "-b", "eval"], ["add", "."],
                 ["-c", "user.name=Eval", "-c", "user.email=eval@example.invalid",
                  "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
                  "commit", "-q", "--allow-empty", "-m", "Eval fixture"]]:
        subprocess.run(["git", *args], cwd=workspace, check=True, capture_output=True, timeout=15)


def metric(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Metrics must be finite nonnegative numbers or null")
    return value


def trial(case, variant, repeat, directory, command, bundle, timeout):
    directory.mkdir()
    workspace = directory / "workspace"
    shutil.copytree(ROOT / "fixtures" / case["fixture"], workspace)
    initialise_repo(workspace)
    before = snapshot(workspace)
    instructions = None
    if variant == "genius":
        instructions = directory / "instructions"
        shutil.copytree(bundle, instructions)
    request = {
        "task_id": case["id"], "prompt": case["prompt"], "workspace": str(workspace),
        "skill_path": str(instructions / "skills" / case["skill"] / "SKILL.md") if instructions else None,
    }
    (directory / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    record = {"task_id": case["id"], "variant": variant, "repeat": repeat,
              "status": "agent_error", "metrics": {}, "metadata": {}, "correct": False}
    started = time.monotonic()
    try:
        code, stdout, stderr, timed_out = execute(command, ROOT.parent, json.dumps(request), timeout)
        (directory / "stdout.json").write_text(stdout)
        (directory / "stderr.txt").write_text(stderr)
        if timed_out:
            record["status"] = "timeout"
        elif code != 0:
            record["error"] = f"Agent exited {code}"
        else:
            record["status"] = "protocol_error"
            response = json.loads(stdout)
            if not isinstance(response.get("text"), str):
                raise ValueError("Adapter must return a text string")
            record["metrics"] = {key: metric(response.get("metrics", {}).get(key)) for key in
                                 ["cost_usd", "input_tokens", "output_tokens", "clarification_tool_calls"]}
            record["metadata"] = response.get("metadata", {})
            (directory / "answer.txt").write_text(response["text"])
            # Agent runtime excludes grading, so check overhead cannot affect the comparison.
            record["duration_seconds"] = time.monotonic() - started
            check = [sys.executable, str(ROOT / "checks.py"), case["id"],
                     str(workspace), str(directory / "answer.txt")]
            code, out, err, timed_out = execute(check, workspace, "", min(timeout, 30))
            (directory / "check.stdout.txt").write_text(out)
            (directory / "check.stderr.txt").write_text(err)
            record["status"] = "check_timeout" if timed_out else "ok"
            record["correct"] = not timed_out and code == 0
    except (OSError, ValueError, TypeError, AttributeError) as error:
        record["error"] = f"{type(error).__name__}: {error}"
    record.setdefault("duration_seconds", time.monotonic() - started)
    after = snapshot(workspace)
    record["changed_files"] = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    record["scope_ok"] = set(record["changed_files"]) <= set(case["allowed_files"])
    record["instructions_ok"] = instructions is None or snapshot(instructions) == snapshot(bundle)
    record["passed"] = record["status"] == "ok" and record["correct"] and record["scope_ok"] and record["instructions_ok"]
    record["review"] = {"unnecessary_questions": None, "notes": "Review answer and trace manually."}
    (directory / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def summarise(records):
    groups = defaultdict(list)
    pairs = defaultdict(dict)
    for row in records:
        groups[row["variant"]].append(row)
        pairs[(row["task_id"], row["repeat"])][row["variant"]] = row["passed"]
    result = {"groups": {}, "paired_passes": {"both": 0, "neither": 0, "genius_only": 0, "baseline_only": 0}}
    for variant, rows in groups.items():
        costs = [row["metrics"].get("cost_usd") for row in rows if row["metrics"].get("cost_usd") is not None]
        result["groups"][variant] = {"runs": len(rows), "passed": sum(row["passed"] for row in rows),
            "errors": sum(row["status"] != "ok" for row in rows),
            "mean_duration_seconds": statistics.mean(row["duration_seconds"] for row in rows),
            "cost_reported_runs": len(costs), "mean_reported_cost_usd": statistics.mean(costs) if costs else None}
    for pair in pairs.values():
        if len(pair) != 2:
            continue
        key = "both" if all(pair.values()) else "neither" if not any(pair.values()) else "genius_only" if pair["genius"] else "baseline_only"
        result["paired_passes"][key] += 1
    return result


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Must be positive")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    agent = parser.add_mutually_exclusive_group(required=True)
    agent.add_argument("--agent-command", help="JSON adapter command, split as arguments; never run through a shell")
    agent.add_argument("--smoke", action="store_true", help="Use the deterministic test adapter; no model calls")
    parser.add_argument("--repeats", type=positive_int, default=3)
    parser.add_argument("--timeout", type=positive_int, default=300)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--genius-root", type=Path, default=ROOT.parent)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if os.name != "posix":
        parser.error("Requires macOS or Linux for process-group cleanup")
    command = [sys.executable, str(ROOT / "tests" / "fake_agent.py")] if args.smoke else shlex.split(args.agent_command)
    if not command:
        parser.error("Agent command cannot be empty")
    cases = json.loads((ROOT / "cases.json").read_text())
    # Write outside the source tree by default; results can contain provider traces.
    directory = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix="genius-evals-"))
    source_root = args.genius_root.resolve()
    if any(source == directory or source in directory.parents
           for source in [source_root / "docs", source_root / "skills", ROOT / "fixtures"]):
        parser.error("Output cannot be inside instruction sources or fixtures")
    if args.output:
        if directory.exists():
            parser.error("Output directory must not already exist")
        directory.mkdir(parents=True)
    bundle = directory / "instructions"
    for name in ["docs", "skills"]:
        source = args.genius_root.resolve() / name
        if not source.is_dir():
            parser.error(f"Missing Genius instruction directory: {source}")
        shutil.copytree(source, bundle / name)
    metadata = {"started_at": datetime.now(timezone.utc).isoformat(), "smoke": args.smoke,
        "agent_command": command, "repeats": args.repeats, "timeout_seconds": args.timeout, "seed": args.seed,
        "instructions_sha256": digest(snapshot(bundle)),
        "suite_sha256": digest({"cases": hashlib.sha256((ROOT / "cases.json").read_bytes()).hexdigest(),
                                "checks": hashlib.sha256((ROOT / "checks.py").read_bytes()).hexdigest(),
                                "fixtures": digest(snapshot(ROOT / "fixtures"))}),
        "python_version": sys.version, "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (directory / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    records = []
    rng = random.Random(args.seed)
    with (directory / "results.jsonl").open("w") as results:
        for repeat in range(1, args.repeats + 1):
            order = list(cases)
            rng.shuffle(order)
            for case in order:
                variants = ["baseline", "genius"]
                rng.shuffle(variants)
                for variant in variants:
                    name = f"{case['id']}-{repeat}-{variant}"
                    row = trial(case, variant, repeat, directory / name, command, bundle, args.timeout)
                    records.append(row)
                    results.write(json.dumps(row) + "\n")
                    results.flush()
                    print(f"{name}: {'PASS' if row['passed'] else 'FAIL'} ({row['status']})", flush=True)
    summary = summarise(records)
    summary["smoke"] = args.smoke
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Results: {directory}")
    return 0 if all(row["passed"] for row in records) else 1


if __name__ == "__main__":
    sys.exit(main())
