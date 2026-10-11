"""Held-out checks. Run in a separate process after the agent finishes."""
import json
from pathlib import Path
import runpy
import sys


def grade(case_id, workspace, text):
    if case_id == "clear-task":
        total = runpy.run_path(str(workspace / "receipt.py"))["total"]
        return all(total(items) == expected for items, expected in [
            ([], 0), ([(3, 4)], 12), ([(3, 0)], 0),
            ([(2, 3), (4, 2)], 14), ([(1.5, 2)], 3),
        ])
    if case_id == "known-preflight":
        config = runpy.run_path(str(workspace / "config.py"))
        client = runpy.run_path(str(workspace / "client.py"))
        if config["TIMEOUT_SECONDS"] != 30 or client["FALLBACK_TIMEOUT"] != 30:
            return False
        if client["timeout"]() != 30 or client["timeout"](5) != 5:
            return False
        try:
            client["timeout"](0)
        except ValueError:
            return True
        return False
    # Accept a Markdown JSON fence, but not arbitrary prose around the answer.
    answer = text.strip()
    if answer.startswith("```json\n") and answer.endswith("\n```"):
        answer = answer[8:-4]
    data = json.loads(answer)
    if not isinstance(data.get("reason"), str) or not 1 <= len(data["reason"].split()) <= 40:
        return False
    if case_id == "small-decision":
        return data.get("choice") == "B"
    if case_id == "decision-review":
        return data.get("decision_was_supported") is True and data.get("change_rule") is False
    raise ValueError(f"Unknown case: {case_id}")


if __name__ == "__main__":
    try:
        ok = grade(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]).read_text())
    except Exception as error:
        print(f"Check failed: {type(error).__name__}: {error}")
        sys.exit(1)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
