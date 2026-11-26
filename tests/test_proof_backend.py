"""Formal corpus and shared skill-loading contracts, checked with Bend 2."""

import os
import re
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
        version = subprocess.run(
            [BEND, "version"], check=True, capture_output=True, text=True, timeout=10
        ).stdout.strip()
        self.assertRegex(version, r"^(?:bend\s+)?2\.")
        sources = sorted(
            [*ROOT.glob("docs/postulates/*.bend"), *ROOT.glob("docs/proofs/*.bend")]
        )
        self.assertTrue(sources)
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


class SkillBackendRouting(unittest.TestCase):
    def test_every_skill_routes_proofs_through_the_shared_backend(self):
        shared = (ROOT / "skills" / "shared" / "proof-backend.md").resolve()
        self.assertTrue(shared.is_file())
        skills = list(ROOT.glob("skills/*/SKILL.md"))
        self.assertTrue(skills)
        for skill in skills:
            with self.subTest(skill=skill.parent.name):
                source = skill.read_text()
                links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", source)
                self.assertIn(
                    shared, [(skill.parent / link).resolve() for link in links]
                )
                hint = next(
                    line
                    for line in source.splitlines()
                    if line.startswith("argument-hint:")
                )
                self.assertNotIn("backend:", hint)
                self.assertNotIn("If GNS-001..006 are not in context", source)


if __name__ == "__main__":
    unittest.main()
