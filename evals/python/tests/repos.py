from pathlib import Path

import pytest

from evals.python.integrations import smoke
from evals.python.integrations.smoke import repo_support, verifier

CASE = '''
[[case]]
id = "drop-deploy"
skill = "improve"
fixture = "release"
scope = ["README.md"]
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


def repo_cases_build_tasks_whose_reference_passes(
    tmp_path: Path, *, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = tmp_path / "cases.toml"
    spec.write_text(CASE)
    (declaration,) = smoke.repo_cases(spec)
    task = declaration.task
    checks = task.checks()
    assert checks is not None
    assert (declaration.skill, tuple(task.allowed_files)) == ("improve", ("README.md",))
    monkeypatch.chdir(tmp_path)
    original = smoke.repo("release")["README.md"]
    Path("README.md").write_text(original)
    assert verifier.verify(("README.md",), checks=checks.stdin)["status"] == "failed"
    (edit,) = task.reference.edits
    Path("README.md").write_text(edit.contents)
    assert verifier.verify(("README.md",), checks=checks.stdin)["status"] == "passed"


def reference_edits_must_match_once_and_stay_in_scope() -> None:
    with pytest.raises(ValueError, match="occur once"):
        smoke.apply({"notes.md": "a\na\n"}, edits=(smoke.Edit(path="notes.md", old="a", new="b"),))
    outside = smoke.RepoCase(
        id="outside",
        skill="improve",
        fixture="release",
        scope=("README.md",),
        prompt="",
        edits=(smoke.Edit(path="CHANGELOG.md", old="x", new="y"),),
        completion="",
        check="",
    )
    with pytest.raises(ValueError, match="inside scope"):
        smoke.repo_task(outside)


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
