import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEND = os.environ.get("BEND_BIN") or shutil.which("bend")


MISMATCHES = {
    "without_recorded_observation": ("False{}", "True{}"),
    "without_norm": ("Empty", "Unit"),
    "relabelled_premise": (
        'T.Dependency{T.Action{1n}, T.Premise{T.Claim{2n, T.ParserCase{"v1", "[1,]"}, T.Predict{T.Accepted{}}}}}',
        'T.Dependency{T.Action{1n}, T.Premise{T.Claim{2n, T.ParserCase{"v1", "[1,]"}, T.Predict{T.Rejected{}}}}}',
    ),
    "without_a_matching_reading_before_action": ("False{}", "True{}"),
    "without_full_enforcement_effects": (
        "@_:Spec.Predicates.Enforcement(ctx) -> Spec.Predicates.EnforcementEffects<ctx>",
        "@_:Spec.Predicates.Enforcement(ctx) -> Spec.Predicates.ValidatedAfter(ctx)",
    ),
    "without_classical_principle": ("Validated", "@_:(@_:Validated -> Empty) -> Empty"),
    "prediction_as_evidence": ("T.Observation<source>", "T.Hypothesis<source>"),
    "observation_from_another_run": (
        'T.Observation<T.TestSuite{"run-2", ".", "asked.py"}>',
        'T.Observation<T.TestSuite{"run-1", ".", "asked.py"}>',
    ),
}


class Corpus(unittest.TestCase):
    def test_each_source_has_a_bend_counterpart(self):
        sources = [
            *ROOT.glob("docs/postulates/[0-9][0-9][0-9]-*.md"),
            *ROOT.glob("docs/proofs/[0-9][0-9][0-9]-*.md"),
        ]
        self.assertTrue(sources)
        for source in sources:
            with self.subTest(source=source.name):
                self.assertTrue(source.with_suffix(".bend").is_file())

    @unittest.skipUnless(
        BEND, "Bend 2 is required for real proof checking; set BEND_BIN"
    )
    def test_all_real_proofs_pass_kernel(self):
        version = subprocess.run(
            [BEND, "version"], check=True, capture_output=True, text=True, timeout=10
        ).stdout.strip()
        self.assertRegex(version, r"^(?:bend\s+)?2\.")
        sources = sorted(
            [*ROOT.glob("docs/postulates/*.bend"), *ROOT.glob("docs/proofs/*.bend")]
        )
        self.assertTrue(sources)
        sources.append(ROOT / "docs/proofs/reasoning/example.bend")
        sources.append(ROOT / "tests/fixtures/proofs/trace.bend")
        for source in sources:
            with self.subTest(source=source.name):
                result = subprocess.run(
                    [BEND, str(source), "--verdict"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=dict(os.environ, BEND_NO_TELEMETRY="1"),
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("ALL PROOFS CHECK", result.stdout)

    @unittest.skipUnless(
        BEND, "Bend 2 is required for invalid-proof checks; set BEND_BIN"
    )
    def test_invalid_derivations_are_rejected_for_the_expected_type_mismatch(self):
        # Numbered proof entries can run directly. Bend imports need a letter first.
        proofs = ROOT / "docs/proofs"
        with tempfile.TemporaryDirectory(prefix="invalid Bend proof ") as temporary:
            target = Path(temporary)
            for name in ("types.bend", "logic.bend", "ooda", "reasoning"):
                module = proofs / name
                (target / name).symlink_to(module, target_is_directory=module.is_dir())
            shutil.copy(proofs / "001-OBSERVATION-PRECEDENCE.bend", target / "GNS001.bend")
            shutil.copy(proofs / "004-INDEPENDENT-PREMISE-VALIDATION.bend", target / "GNS004.bend")
            for name, (expected, observed) in MISMATCHES.items():
                fixture = ROOT / "tests/fixtures/proofs/invalid" / f"{name}.bend"
                with self.subTest(fixture=fixture.stem):
                    source = shutil.copy(fixture, target)
                    result = subprocess.run(
                        [BEND, source, "--check-only"],
                        capture_output=True, text=True, timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    output = result.stdout + result.stderr
                    self.assertIn(f"- expected : {expected}\n", output)
                    self.assertIn(f"- observed : {observed}\n", output)


if __name__ == "__main__":
    unittest.main()
