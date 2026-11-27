import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEND = os.environ.get("BEND_BIN") or shutil.which("bend")


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
        fixtures = {
            "without_recorded_observation": (
                (
                    "import ./Proof-001-OBSERVATION-PRECEDENCE.bend as GNS001\n"
                    "import ./ooda/main.bend as Loop\n"
                    "def bad() -> Empty:\n"
                    "  GNS001.theorem(2n, False{}, T.AttemptKey{1n, 1n}, Nil{}, Inl{{==}}, {==})\n"
                ),
                "False{}",
                "True{}",
            ),
            "without_norm": (
                (
                    "import ./Proof-004-INDEPENDENT-PREMISE-VALIDATION.bend as GNS004\n"
                    "def bad() -> (Empty -> Empty) -> Empty:\n"
                    "  GNS004.validation_burden(Unit, Unit, Unit, Unit, Empty, Unit, Unit,\n"
                    "    n => n, o => o, classified => Unit{}, assumed => Unit{}, risk => risk,\n"
                    "    Logic.Conjunction{Unit{}, Unit{}})\n"
                ),
                "Empty",
                "Unit",
            ),
            "with_derived_confirmation_only": (
                (
                    "import ./Proof-004-INDEPENDENT-PREMISE-VALIDATION.bend as GNS004\n"
                    "import ./reasoning/main.bend as Model\n"
                    "import ./reasoning/SPEC.bend as Spec\n"
                    "def ctx() -> T.Context<T.ActionUse>:\n"
                    "  T.Frame{0n, T.Use{1n, 2n, 2n, False{}},\n"
                    "    T.Dependency{T.Action{1n}, T.Premise{2n}} <>\n"
                    "      T.Confirmation{2n, T.Derived{}} <> Nil{},\n"
                    "    Nil{}, T.NoIntervention{}}\n"
                    "def bad() -> Spec.Predicates.ValidatedBefore(ctx()):\n"
                    "  GNS004.theorem(ctx(), (Inl{{==}}, Inl{{==}}), {==})\n"
                ),
                "False{}",
                "True{}",
            ),
            "without_full_enforcement_effects": (
                (
                    "import ./reasoning/main.bend as Model\n"
                    "import ./reasoning/SPEC.bend as Spec\n"
                    "def bad(+ctx: T.Context<T.ExternalUse>,\n"
                    "  applicable: Spec.Predicates.PremiseRequiredBefore(Model.action_context(ctx)),\n"
                    "  forward: Spec.Premises.Forward<ctx>,\n"
                    "  validates: Spec.Predicates.Enforcement(ctx) -> Spec.Predicates.ValidatedAfter(ctx)\n"
                    ") -> Spec.Premises.Enforcement<ctx>:\n"
                    "  Spec.EnforcementPremises{applicable, forward, validates}\n"
                ),
                "@_:Spec.Predicates.Enforcement(ctx) -> Spec.Predicates.EnforcementEffects<ctx>",
                "@_:Spec.Predicates.Enforcement(ctx) -> Spec.Predicates.ValidatedAfter(ctx)",
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
                # Bend 2.0.40 accepts numbered entry files, but imports must start with a letter.
                name = "Proof-" + source.name if source.name[0].isdigit() else source.name
                shutil.copy(source, target / name)
            for name in ("ooda", "reasoning"):
                shutil.copytree(ROOT / "docs/proofs" / name, target / name)
            for name, (body, expected, observed) in fixtures.items():
                with self.subTest(name=name):
                    path = target / f"{name}.bend"
                    path.write_text(
                        "import Base\nimport ./logic.bend as Logic\nimport ./types.bend as T\n" + body
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
