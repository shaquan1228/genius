from pathlib import Path

import pytest
from kernel import ValidationError, Verification

from evals.python.integrations import smoke
from evals.python.integrations.smoke import repo_support, verifier

CASE = '''
[[case]]
id = "drop-deploy"
skill = "improve"
fixture = "release"
scope = ["README.md", "CHANGELOG.md"]
prompt = "Remove deploy.sh from the README."
completion = "Removed it."
check = """
added, removed = delta("README.md")
assert added == [] and len(removed) == 1 and "deploy.sh" in removed[0], (added, removed)
"""

[[case.edits]]
path = "README.md"
old = "- `deploy.sh`: upload the wheel to the package index.\\n"
new = ""
'''


def repo_reads_every_fixture_file() -> None:
    assert set(smoke.repo("release")) == {"CHANGELOG.md", "README.md", "RELEASING.md", "build.sh"}


def suite_fixture_ignores_python_cache(tmp_path: Path, *, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smoke, "REPOS", tmp_path)
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "__pycache__").mkdir()
    (suite / "parser_test.py").write_text("import unittest")
    assert smoke.repo("suite") == {"parser_test.py": "import unittest"}


def repo_cases_build_tasks_whose_reference_passes(
    tmp_path: Path, *, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = tmp_path / "cases.toml"
    spec.write_text(CASE)
    (declaration,) = smoke.load_cases(spec)
    task = declaration.task
    checks = task.checks()
    assert checks is not None
    assert (declaration.skill, checks.inputs) == ("improve", ("README.md", "CHANGELOG.md"))
    monkeypatch.chdir(tmp_path)
    original = smoke.repo("release")
    Path("README.md").write_text(original["README.md"])
    Path("CHANGELOG.md").write_text(original["CHANGELOG.md"])
    before = verifier.verify(checks.inputs, checks=checks.stdin)["status"]
    (edit,) = task.reference.edits
    Path("README.md").write_text(edit.contents)
    after = verifier.verify(checks.inputs, checks=checks.stdin)["status"]
    assert (edit.path, before, after) == ("README.md", "failed", "passed")


def answer_cases_grade_expected_fields(tmp_path: Path) -> None:
    spec = tmp_path / "cases.toml"
    spec.write_text(
        '[[case]]\nid = "pick"\nskill = "bayesian"\nprompt = "Pick A or B."\n'
        'expected = { choice = "B", sure = true }\nreason = "B is cheaper."\n'
    )
    (declaration,) = smoke.load_cases(spec)
    task = declaration.task
    assert (task.checks(), tuple(task.allowed_files), tuple(task.fixture)) == (None, (), ())
    assert task.reference.completion.to_python() == {
        "choice": "B",
        "sure": True,
        "reason": "B is cheaper.",
    }
    assert all(dict(task.grade_reference(verification=Verification.Unchecked())).values())


def cases_must_match_one_shape(tmp_path: Path) -> None:
    spec = tmp_path / "cases.toml"
    spec.write_text(
        '[[case]]\nid = "pick"\nskill = "bayesian"\nprompt = ""\nexpected = {}\n'
        'reason = ""\nscope = ["README.md"]\n'
    )
    with pytest.raises(ValueError, match="scope"):
        smoke.load_cases(spec)


def reference_edits_must_match_once_and_stay_in_scope() -> None:
    with pytest.raises(ValueError, match="occur once"):
        smoke.apply({"notes.md": "a\na\n"}, edits=(smoke.Edit(path="notes.md", old="a", new="b"),))
    outside = smoke.RepoCase(
        id="outside",
        skill="improve",
        fixture="release",
        scope=("README.md",),
        prompt="",
        edits=(smoke.Edit(path="CHANGELOG.md", old="# Changelog", new="# Release history"),),
        completion="",
        check="",
    )
    with pytest.raises(ValidationError) as error:
        smoke.repo_task(outside)
    assert [issue.field for issue in error.value.issues] == ["reference.edits"]
    typo = outside.model_copy(update={"edits": (smoke.Edit(path="CHANGLOG.md", old="x", new="y"),)})
    with pytest.raises(ValueError, match=r"missing from the fixture: CHANGLOG\.md"):
        smoke.repo_task(typo)


def repo_support_compares_against_the_fixture(
    tmp_path: Path, *, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(repo_support, "ORIGINAL", {"doc.md": "# A\n\n- one\n# B\n- two\n"})
    Path("doc.md").write_text("# A\n\n- one\n- new\n# B\n")
    assert repo_support.delta("doc.md") == (["- new"], ["- two"])
    assert repo_support.section("doc.md", heading="# A") == ["", "- one", "- new"]
    assert repo_support.section("doc.md", heading="# B") == []


def verifier_skips_syntax_checks_for_text_inputs(
    tmp_path: Path, *, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("notes.md").write_text("def broken(:\n")
    assert verifier.verify(("notes.md",), checks="")["status"] == "passed"
