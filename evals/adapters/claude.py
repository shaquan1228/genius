#!/usr/bin/env python3
"""Bridge the runner's JSON protocol to Claude Code print mode."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def command(args, request):
    # Bare mode excludes installed plugins, CLAUDE.md, hooks, and auto memory.
    result = ["claude", "--bare", "--print", "--output-format", "stream-json", "--verbose",
              "--no-session-persistence", "--model", args.model, "--effort", args.effort,
              "--max-turns", str(args.max_turns), "--max-budget-usd", str(args.max_budget_usd),
              "--tools", "Bash,Edit,Write,Read,Glob,Grep,AskUserQuestion",
              "--allowedTools", "Bash,Edit,Write,Read,Glob,Grep"]
    if request.get("skill_path"):
        path = Path(request["skill_path"])
        result += ["--add-dir", str(path.parents[2]), "--append-system-prompt",
                   f"Read and apply the Genius skill at {path} before working on the supplied task."]
    return result


def normalise(events, args, version):
    results = [event for event in events if event.get("type") == "result"]
    if len(results) != 1:
        raise ValueError("Expected exactly one Claude result event")
    result = results[0]
    uses = [block for event in events if event.get("type") == "assistant"
            for block in event.get("message", {}).get("content", []) if block.get("type") == "tool_use"]
    usage = result.get("usage", {})
    return {"text": result.get("result", ""), "trace": events,
            "metrics": {"cost_usd": result.get("total_cost_usd"),
                        "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
                        "clarification_tool_calls": sum(block.get("name") == "AskUserQuestion" for block in uses)},
            "metadata": {"agent": "claude", "version": version, "model_requested": args.model,
                         "models_reported": sorted(result.get("modelUsage", {})), "effort": args.effort,
                         "max_turns": args.max_turns, "max_budget_usd": args.max_budget_usd,
                         "result_subtype": result.get("subtype"),
                         "is_error": result.get("is_error", False) or result.get("subtype") != "success"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Use a pinned model ID for repeatable comparisons")
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high", "max"])
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--max-budget-usd", type=float, default=2.0)
    args = parser.parse_args()
    if args.max_turns < 1 or not 0 < args.max_budget_usd < float("inf"):
        parser.error("Turn and cost limits must be positive and finite")
    request = json.load(sys.stdin)
    version = subprocess.run(["claude", "--version"], capture_output=True, text=True, check=True, timeout=15).stdout.strip()
    process = subprocess.run(command(args, request), cwd=request["workspace"], input=request["prompt"],
                             capture_output=True, text=True)
    events = [json.loads(line) for line in process.stdout.splitlines() if line.strip()]
    response = normalise(events, args, version)
    print(json.dumps(response))
    if process.stderr:
        print(process.stderr, file=sys.stderr, end="")
    return 1 if process.returncode or response["metadata"]["is_error"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Claude adapter failed: {error}", file=sys.stderr)
        sys.exit(1)
