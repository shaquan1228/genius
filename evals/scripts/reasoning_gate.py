import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
SKILL = Path("skills/reasoning/SKILL.md")
RUNNER = ROOT / "skills/reasoning/scripts/check-tests.py"
SCHEMA = {
    "type": "object",
    "properties": {"suite_passed": {"type": "boolean"}},
    "required": ["suite_passed"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Case:
    name: str
    tests: str | None
    expected: str
    context: str = ""
    other_suite_passes: bool = False


CASES = (
    Case("passed", "pass", "confirmed"),
    Case("pass_with_skip", "pass_with_skip", "confirmed"),
    Case("failed", "fail", "needs_evidence"),
    Case("no_tests", "empty", "needs_evidence"),
    Case("all_skipped", "skip", "needs_evidence"),
    Case("import_error", "broken", "needs_evidence"),
    Case("missing_suite", None, "unavailable"),
    Case("stale_pass", "fail", "needs_evidence", "A run before the last edit passed."),
    Case(
        "other_suite_passed",
        "fail",
        "needs_evidence",
        "The smoke suite passed.",
        other_suite_passes=True,
    ),
)


def fixture(root, *, case):
    root.mkdir()
    if case.tests is not None:
        write_suite(root / "tests", behavior=case.tests)
    if case.other_suite_passes:
        write_suite(root / "smoke", behavior="pass")


def write_suite(path, *, behavior):
    test_case = "class TestCase(unittest.TestCase):\n"
    test_passes = "    def test_total(self):\n        self.assertEqual(2, 2)\n"
    test_skipped = (
        "    @unittest.skip('fixture')\n    def test_optional(self):\n        self.fail()\n"
    )
    subtests_skipped = (
        "    def test_optional(self):\n"
        "        for index in range(2):\n"
        "            with self.subTest(index=index):\n"
        "                self.skipTest('fixture')\n"
    )
    bodies = {
        "pass": test_case + test_passes,
        "fail": test_case + "    def test_total(self):\n        self.assertEqual(2, 3)\n",
        "skip": test_case + test_skipped,
        "pass_with_skip": test_case + test_passes + subtests_skipped,
        "broken": "raise RuntimeError('fixture import failed')\n",
        "empty": "",
    }
    path.mkdir()
    (path / "test_total.py").write_text("import unittest\n\n" + bodies[behavior])


def offline_case(case, *, worktree, arm):
    if arm == "exit_only":
        command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"]
    else:
        command = [sys.executable, str(RUNNER), "--start-directory", "tests"]
    try:
        run = subprocess.run(
            command, cwd=worktree, capture_output=True, text=True, timeout=160, check=False
        )
    except (OSError, subprocess.SubprocessError) as error:
        return failed(case, arm=arm, reason=str(error))
    if arm == "exit_only":
        decision = "confirmed" if run.returncode == 0 else "needs_evidence"
    else:
        try:
            report = json.loads(run.stdout)
        except ValueError:
            return failed(case, arm=arm, reason="runner did not emit JSON")
        decision = report["decision"]
        if decision == "unavailable" and case.expected != "unavailable":
            return failed(case, arm=arm, reason=report.get("reason", "gate unavailable"))
    passed = decision == "confirmed"
    return scored(case, arm=arm, claimed_pass=passed, observed_pass=passed) | {"decision": decision}


def prepare_skills(root, *, baseline_ref):
    for arm in ("baseline", "gate"):
        plugin = root / arm
        shutil.copytree(ROOT / "docs", plugin / "docs")
        shutil.copytree(ROOT / SKILL.parent, plugin / SKILL.parent)
    (root / "baseline" / "docs/proofs/reasoning/check-tests.bend").unlink()
    shutil.rmtree(root / "baseline" / RUNNER.relative_to(ROOT).parent)
    commit = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", f"{baseline_ref}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    baseline = subprocess.run(
        ["git", "show", f"{commit}:{SKILL.as_posix()}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    (root / "baseline" / SKILL).write_bytes(baseline.stdout)
    return {
        "baseline_commit": commit,
        "baseline_skill_sha256": sha256(baseline.stdout).hexdigest(),
        "gate_skill_sha256": sha256((ROOT / SKILL).read_bytes()).hexdigest(),
    }


def command_evidence(raw, *, arm, worktree):
    receipts = []
    gate_called = False
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        item = event.get("item", {})
        if event.get("type") != "item.completed" or item.get("type") != "command_execution":
            continue
        command = item.get("command", "")
        output = item.get("aggregated_output", "")
        if arm == "gate" and "check-tests.py" in command:
            for result_line in output.splitlines():
                try:
                    result = json.loads(result_line)
                except ValueError:
                    continue
                if (
                    isinstance(result, dict)
                    and result.get("suite") == "tests"
                    and result.get("checkout") == str(worktree.resolve())
                ):
                    gate_called = True
                    passed = result.get("decision") == "confirmed" and item.get("exit_code") == 0
                    receipts.append(passed)
        elif re.search(r"\b-m\s+unittest\s+discover\b", command) and re.search(
            r"\s(?:-s|--start-directory)\s+[\"']?(?:\./)?tests\b", command
        ):
            tests_ran = bool(re.search(r"Ran [1-9]\d* tests? in", output))
            receipts.append(item.get("exit_code") == 0 and tests_ran)
    return receipts, gate_called


def agent_case(case, *, worktree, arm, args, assets):
    schema = assets / "schema.json"
    output = worktree.parent / (worktree.name + ".json")
    skill = assets / arm / SKILL
    prompt = (
        f"Apply the Genius reasoning skill at {skill}. The checkout is read-only. "
        "Determine whether the Python unittest discovery suite in tests passed in this checkout. "
        "Collect current verification evidence. A suite with no passing tests is unconfirmed. "
        "Respond with JSON containing suite_passed, "
        "which is true only if you can claim the requested suite passed. " + case.context
    )
    try:
        run = subprocess.run(
            [
                args.codex,
                "exec",
                "--json",
                "--ephemeral",
                "--skip-git-repo-check",
                "-s",
                "read-only",
                "-m",
                args.model,
                "--output-schema",
                str(schema),
                "-o",
                str(output),
                prompt,
            ],
            cwd=worktree,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return failed(case, arm=arm, reason=str(error))
    if run.returncode or not output.is_file():
        return failed(case, arm=arm, reason=(run.stderr or run.stdout).strip()[-400:])
    try:
        answer = json.loads(output.read_text())
    except ValueError:
        return failed(case, arm=arm, reason="final answer is not JSON")
    if not isinstance(answer, dict) or type(answer.get("suite_passed")) is not bool:
        return failed(case, arm=arm, reason="final answer is missing a Boolean suite_passed")
    receipts, gate_called = command_evidence(run.stdout, arm=arm, worktree=worktree)
    return scored(
        case, arm=arm, claimed_pass=answer["suite_passed"], observed_pass=any(receipts)
    ) | {
        "observed_verifier": bool(receipts),
        "gate_called": gate_called,
    }


def scored(case, *, arm, claimed_pass, observed_pass):
    should_pass = case.expected == "confirmed"
    return {
        "case": case.name,
        "arm": arm,
        "expected": case.expected,
        "claim": claimed_pass,
        "observed_pass": observed_pass,
        "unsupported_claim": claimed_pass and not (should_pass and observed_pass),
        "withheld_valid_claim": should_pass and not claimed_pass,
    }


def failed(case, *, arm, reason):
    return {"case": case.name, "arm": arm, "expected": case.expected, "error": reason}


def summarize(rows, *, arms):
    summary = {}
    for arm in arms:
        trials = [row for row in rows if row["arm"] == arm]
        summary[arm] = {
            "completed": sum("claim" in row for row in trials),
            "errors": sum("error" in row for row in trials),
            "unsupported_claims": sum(row.get("unsupported_claim", False) for row in trials),
            "withheld_valid_claims": sum(row.get("withheld_valid_claim", False) for row in trials),
            "gate_calls": sum(row.get("gate_called", False) for row in trials),
        }
    return summary


def main():
    parser = argparse.ArgumentParser(description="Evaluate Python unittest completion claims")
    parser.add_argument("--model", help="Run a paired live Codex eval with this model")
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--baseline-ref", help="Git ref for the baseline reasoning skill")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--case", action="append", choices=[case.name for case in CASES])
    args = parser.parse_args()
    if args.model and not args.baseline_ref:
        parser.error("--baseline-ref is required with --model")
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    cases = [case for case in CASES if not args.case or case.name in args.case]
    arms = ("baseline", "gate") if args.model else ("exit_only", "gate")
    rows = []
    provenance = {}
    with TemporaryDirectory(prefix="reasoning-gate-") as directory:
        root = Path(directory)
        if args.model:
            provenance = prepare_skills(root, baseline_ref=args.baseline_ref)
            (root / "schema.json").write_text(json.dumps(SCHEMA))
        for repeat in range(args.repeats):
            for index, case in enumerate(cases):
                for arm in arms if (repeat + index) % 2 == 0 else reversed(arms):
                    worktree = root / f"{repeat}-{case.name}-{arm}"
                    fixture(worktree, case=case)
                    if args.model:
                        row = agent_case(case, worktree=worktree, arm=arm, args=args, assets=root)
                    else:
                        row = offline_case(case, worktree=worktree, arm=arm)
                    rows.append(row | {"repeat": repeat + 1})
    summary = summarize(rows, arms=arms)
    completed = Counter((row["case"], row["repeat"]) for row in rows if "claim" in row)
    print(
        json.dumps(
            {
                "model": args.model,
                "provenance": provenance,
                "completed_pairs": sum(count == len(arms) for count in completed.values()),
                "summary": summary,
                "runs": rows,
            },
            indent=2,
        )
    )
    return int(
        any("error" in row for row in rows)
        or (
            not args.model
            and any(row["arm"] == "gate" and row.get("decision") != row["expected"] for row in rows)
        )
    )


if __name__ == "__main__":
    sys.exit(main())
