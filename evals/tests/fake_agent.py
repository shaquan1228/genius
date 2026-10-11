"""Deterministic test double. It does not evaluate a language model."""
import json
from pathlib import Path
import sys
import time

request = json.load(sys.stdin)
workspace = Path(request["workspace"])
mode = sys.argv[1] if len(sys.argv) > 1 else "pass"
if mode == "timeout":
    time.sleep(60)
if mode == "invalid":
    print("not JSON")
    sys.exit(0)
if mode == "fail":
    print("test failure", file=sys.stderr)
    sys.exit(1)

if request["task_id"] == "clear-task":
    (workspace / "receipt.py").write_text("def total(items):\n    return sum(price * quantity for price, quantity in items)\n")
    text = "Fixed quantity handling."
elif request["task_id"] == "known-preflight":
    for name in ["client.py", "config.py"]:
        path = workspace / name
        path.write_text(path.read_text().replace("= 15", "= 30"))
    text = "Updated both defaults to 30."
elif request["task_id"] == "small-decision":
    text = json.dumps({"choice": "B", "reason": "Identical service costs $2 less."})
else:
    text = json.dumps({"decision_was_supported": True, "change_rule": False, "reason": "One loss does not change known odds."})
if mode == "scope":
    (workspace / "unrequested.txt").write_text("Extra change")
if mode == "instructions" and request["skill_path"]:
    Path(request["skill_path"]).write_text("Changed shared rules")
print(json.dumps({"text": text, "metrics": {}, "metadata": {"agent": "test-double"}}))
