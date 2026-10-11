import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import checks
import run

spec = importlib.util.spec_from_file_location("claude_adapter", ROOT / "adapters" / "claude.py")
claude = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claude)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.bundle = self.directory / "bundle"
        for name in ["docs", "skills"]:
            run.shutil.copytree(ROOT.parent / name, self.bundle / name)
        self.case = json.loads((ROOT / "cases.json").read_text())[0]

    def tearDown(self):
        self.temp.cleanup()

    def trial(self, mode="pass", variant="baseline"):
        command = [sys.executable, str(ROOT / "tests" / "fake_agent.py"), mode]
        return run.trial(self.case, variant, 1, self.directory / "trial", command, self.bundle, 1 if mode == "timeout" else 10)

    def test_correct_task_passes_without_exposing_genius_to_baseline(self):
        result = self.trial()
        self.assertTrue(result["passed"])
        request = json.loads((self.directory / "trial" / "request.json").read_text())
        self.assertIsNone(request["skill_path"])
        self.assertEqual(result["changed_files"], ["receipt.py"])
        self.assertIsNone(result["metrics"]["cost_usd"])

    def test_extra_edit_fails_scope_even_when_answer_is_correct(self):
        result = self.trial("scope")
        self.assertTrue(result["correct"])
        self.assertFalse(result["scope_ok"])
        self.assertFalse(result["passed"])

    def test_untouched_bug_fails_the_held_out_check(self):
        self.assertFalse(checks.grade("clear-task", ROOT / "fixtures" / "clear-task", "Done"))

    def test_corrupted_instructions_fail_without_changing_next_trial(self):
        before = run.snapshot(self.bundle)
        result = self.trial("instructions", "genius")
        self.assertFalse(result["instructions_ok"])
        self.assertFalse(result["passed"])
        self.assertEqual(run.snapshot(self.bundle), before)

    def test_invalid_output_is_not_a_pass(self):
        self.assertEqual(self.trial("invalid")["status"], "protocol_error")

    def test_agent_failure_is_not_a_pass(self):
        self.assertEqual(self.trial("fail")["status"], "agent_error")

    def test_timeout_is_recorded(self):
        result = self.trial("timeout")
        self.assertEqual(result["status"], "timeout")
        self.assertFalse(result["passed"])

    def test_fresh_trials_do_not_inherit_the_previous_edit(self):
        self.assertTrue(self.trial()["passed"])
        other = run.trial(self.case, "genius", 1, self.directory / "other",
                          [sys.executable, str(ROOT / "tests" / "fake_agent.py")], self.bundle, 10)
        self.assertEqual(other["changed_files"], ["receipt.py"])

    def test_wrong_decision_and_hindsight_verdict_fail(self):
        self.assertFalse(checks.grade("small-decision", self.directory, '{"choice":"A","reason":"Cheaper"}'))
        self.assertFalse(checks.grade("decision-review", self.directory,
                                     '{"decision_was_supported":false,"change_rule":true,"reason":"Lost"}'))

    def test_complete_smoke_suite_and_repeat_pairing(self):
        output = self.directory / "results"
        self.assertEqual(run.main(["--smoke", "--repeats", "2", "--output", str(output)]), 0)
        rows = [json.loads(line) for line in (output / "results.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 16)
        summary = json.loads((output / "summary.json").read_text())
        self.assertTrue(summary["smoke"])
        self.assertEqual(summary["paired_passes"]["both"], 8)
        self.assertIsNone(summary["groups"]["baseline"]["mean_reported_cost_usd"])


class AdapterTests(unittest.TestCase):
    def test_cli_entrypoint_with_mock_provider_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "claude"
            executable.write_text(f"#!{sys.executable}\nimport json, sys\n"
                                  "if '--version' in sys.argv:\n    print('mock-cli'); sys.exit(0)\n"
                                  "assert '--bare' in sys.argv\nassert sys.stdin.read() == 'Task'\n"
                                  "print(json.dumps({'type':'result', 'subtype':'success', 'is_error':False, "
                                  "'result':'Done', 'total_cost_usd':0.05, 'usage':{}, 'modelUsage':{'pinned-model':{}}}))\n")
            executable.chmod(0o755)
            request = {"prompt": "Task", "workspace": directory, "skill_path": None}
            process = run.subprocess.run([sys.executable, str(ROOT / "adapters" / "claude.py"),
                                          "--model", "pinned-model"], input=json.dumps(request),
                                         capture_output=True, text=True,
                                         env={**os.environ, "PATH": directory + os.pathsep + os.environ["PATH"]}, timeout=10)
            self.assertEqual(process.returncode, 0, process.stderr)
            response = json.loads(process.stdout)
            self.assertEqual(response["metrics"]["cost_usd"], 0.05)
            self.assertEqual(response["metadata"]["version"], "mock-cli")

    def test_same_settings_and_genius_only_instruction_addition(self):
        args = argparse.Namespace(model="pinned-model", effort="medium", max_turns=20, max_budget_usd=2)
        baseline = claude.command(args, {"skill_path": None})
        genius = claude.command(args, {"skill_path": "/tmp/rules/skills/reasoning/SKILL.md"})
        self.assertEqual(genius[:len(baseline)], baseline)
        self.assertIn("--bare", baseline)
        self.assertNotIn("--append-system-prompt", baseline)
        self.assertIn("--append-system-prompt", genius)

    def test_normalises_real_event_shape_and_unknown_cost(self):
        args = argparse.Namespace(model="pinned-model", effort="medium", max_turns=20, max_budget_usd=2)
        events = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "AskUserQuestion"}]}},
                  {"type": "result", "subtype": "success", "is_error": False, "result": "Done",
                   "usage": {"input_tokens": 10, "output_tokens": 4}, "modelUsage": {"pinned-model": {}}}]
        result = claude.normalise(events, args, "test-version")
        self.assertEqual(result["text"], "Done")
        self.assertEqual(result["metrics"]["clarification_tool_calls"], 1)
        self.assertIsNone(result["metrics"]["cost_usd"])
        self.assertEqual(result["metadata"]["models_reported"], ["pinned-model"])


if __name__ == "__main__":
    unittest.main()
