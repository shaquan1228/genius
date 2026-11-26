"""Backend selection contracts plus opt-in checks using the real Bend 2 compiler."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "bin" / "genius-proof"
BEND = os.environ.get("BEND_BIN") or shutil.which("bend")


class BackendSelection(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="proof backend ")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        (self.repo / "bin").mkdir()
        shutil.copy(COMMAND, self.repo / "bin" / "genius-proof")
        self.proofs = self.repo / "docs" / "proofs"
        self.proofs.mkdir(parents=True)
        (self.proofs / "001-TEST.md").write_text("Markdown treatment\n")
        (self.proofs / "GNS-001-TEST.bend").write_text("Bend treatment\n")
        self.log = self.repo / "calls"
        self.fake = self.repo / "compiler"
        self.fake.write_text(
            f"#!{sys.executable}\n"
            "import json, os, pathlib, sys\n"
            "if sys.argv[1:] == ['version']:\n"
            " print(os.environ.get('TEST_BEND_VERSION', 'bend 2.0.40'))\n"
            "else:\n"
            " with pathlib.Path(os.environ['TEST_CALL_LOG']).open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')\n"
            " print('SOME PROOFS FAIL' if os.environ.get('TEST_BEND_FAIL') else 'ALL PROOFS CHECK')\n"
            " sys.exit(1 if os.environ.get('TEST_BEND_FAIL') else 0)\n"
        )
        self.fake.chmod(0o755)

    def run_command(self, *arguments, **environment):
        return subprocess.run(
            [sys.executable, str(self.repo / "bin" / "genius-proof"), *arguments],
            check=False,
            cwd=self.temporary.name,
            capture_output=True,
            text=True,
            timeout=15,
            env=dict(os.environ, TEST_CALL_LOG=str(self.log), **environment),
        )

    def test_markdown_is_default_and_does_not_need_a_compiler(self):
        result = self.run_command("GNS-001", "--bend", "/not/a/compiler")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Markdown treatment", result.stdout)
        self.assertIn("no machine-checked proof claim", result.stdout)
        self.assertFalse(self.log.exists())

    def test_bend_runs_kernel_and_returns_only_bend_treatment(self):
        result = self.run_command(
            "--backend", "bend", "--bend", str(self.fake), "gns-001"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Bend treatment", result.stdout)
        self.assertNotIn("Markdown treatment", result.stdout)
        self.assertIn("--verdict", self.log.read_text())

    def test_failure_cannot_fall_back_to_markdown(self):
        result = self.run_command(
            "--backend", "bend", "--bend", str(self.fake), TEST_BEND_FAIL="1"
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Bend check failed", result.stderr)

    def test_missing_toolchain_cannot_fall_back(self):
        result = self.run_command("--backend", "bend", "--bend", "/not/a/compiler")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")

    def test_missing_bend_counterpart_cannot_fall_back(self):
        (self.proofs / "GNS-001-TEST.bend").unlink()
        result = self.run_command("--backend", "bend", "--bend", str(self.fake))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")

    def test_rejects_bend_one(self):
        result = self.run_command(
            "--backend",
            "bend",
            "--bend",
            str(self.fake),
            TEST_BEND_VERSION="bend 1.0.0",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Bend 2 required", result.stderr)
        self.assertFalse(self.log.exists())

    def test_weaker_checker_requires_explicit_selection_and_is_labeled(self):
        result = self.run_command(
            "--backend", "bend", "--bend", str(self.fake), "--ordinary", "--check-only"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ordinary checker accepted", result.stdout)
        self.assertNotIn("Bend treatment", result.stdout)
        self.assertIn("--check-only", self.log.read_text())
        rejected = self.run_command("--ordinary")
        self.assertEqual(rejected.returncode, 1)

    def test_unknown_identity_is_an_error(self):
        result = self.run_command("GNS-999")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unknown proof identity", result.stderr)

    def test_empty_corpus_is_an_error(self):
        shutil.rmtree(self.repo / "docs")
        result = self.run_command("--check-only")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("No postulate or proof sources", result.stderr)

    def test_postulate_status_does_not_claim_to_prove_hypothesis(self):
        folder = self.repo / "docs" / "postulates"
        folder.mkdir()
        (folder / "001-TEST.md").write_text("Open question")
        (folder / "POSTULATE-001-TEST.bend").write_text("Hypothesis")
        result = self.run_command(
            "POSTULATE-001",
            "--backend",
            "bend",
            "--bend",
            str(self.fake),
            "--check-only",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "hypothesis stated, conditional consequences checked", result.stdout
        )


class Corpus(unittest.TestCase):
    def test_each_source_has_a_bend_counterpart(self):
        sources = [
            *ROOT.glob("docs/postulates/[0-9][0-9][0-9]-*.md"),
            *ROOT.glob("docs/proofs/[0-9][0-9][0-9]-*.md"),
        ]
        self.assertEqual(len(sources), 7)
        for source in sources:
            with self.subTest(source=source.name):
                prefix = "POSTULATE" if source.parent.name == "postulates" else "GNS"
                self.assertTrue(
                    source.with_name(
                        prefix + "-" + source.with_suffix(".bend").name
                    ).is_file()
                )

    @unittest.skipUnless(
        BEND, "Bend 2 is required for real proof checking; set BEND_BIN"
    )
    def test_all_real_proofs_pass_kernel(self):
        result = subprocess.run(
            [
                sys.executable,
                str(COMMAND),
                "--backend",
                "bend",
                "--bend",
                BEND,
                "--check-only",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("Lean-backed kernel accepted"), 7)

    @unittest.skipUnless(
        BEND, "Bend 2 is required for invalid-proof checks; set BEND_BIN"
    )
    def test_invalid_derivations_are_rejected_for_the_expected_type_mismatch(self):
        fixtures = {
            "without_observation_implication": (
                (
                    "import ./GNS-001-OBSERVATION-PRECEDENCE.bend as GNS001\n"
                    "def bad(-N: Type, -O: Type, -F: Type, -P: Type, p1: N -> O, p2: O -> F) -> N -> P:\n"
                    "  GNS001.theorem(N, O, F, P, p1, p2, first => first)\n"
                ),
                "P",
                "F",
            ),
            "without_norm": (
                (
                    "import ./GNS-004-INDEPENDENT-PREMISE-VALIDATION.bend as GNS004\n"
                    "def bad() -> (Empty -> Empty) -> Empty:\n"
                    "  GNS004.validation_burden(Unit, Unit, Unit, Unit, Empty, Unit, Unit,\n"
                    "    n => n, o => o, classified => Unit{}, assumed => Unit{}, risk => risk,\n"
                    "    Logic.Conjunction{Unit{}, Unit{}})\n"
                ),
                "Empty",
                "Unit",
            ),
            "without_classical_principle": (
                (
                    "def bad(-Validated: Type, burden: (Validated -> Empty) -> Empty) -> Validated:\n"
                    "  burden\n"
                ),
                "Validated",
                "@_:(@_:Validated -> Empty) -> Empty",
            ),
        }
        with tempfile.TemporaryDirectory(prefix="invalid Bend proof ") as temporary:
            target = Path(temporary)
            for source in ROOT.glob("docs/proofs/*.bend"):
                shutil.copy(source, target / source.name)
            for name, (body, expected, observed) in fixtures.items():
                with self.subTest(name=name):
                    path = target / f"{name}.bend"
                    path.write_text(
                        "import Base\nimport ./logic.bend as Logic\n" + body
                    )
                    result = subprocess.run(
                        [BEND, str(path), "--check-only"],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    output = result.stdout + result.stderr
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f"- expected : {expected}\n", output)
                    self.assertIn(f"- observed : {observed}\n", output)


if __name__ == "__main__":
    unittest.main()
