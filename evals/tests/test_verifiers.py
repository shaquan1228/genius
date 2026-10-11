"""Test held-out graders against seeded bugs and plausible incorrect fixes."""

import shutil
from pathlib import Path

import pytest

from genius_evals.cases import EVALS_ROOT
from genius_evals.verifiers import preflight, receipt
from tests.scenarios import EDITS


def test_receipt_seed_is_incorrect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shutil.copytree(EVALS_ROOT / "fixtures/clear-task", tmp_path, dirs_exist_ok=True)
    monkeypatch.chdir(tmp_path)
    assert not receipt.verify()


def test_receipt_fix_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "receipt.py").write_text(EDITS["clear-task"]["receipt.py"])
    monkeypatch.chdir(tmp_path)
    assert receipt.verify()


@pytest.mark.parametrize(
    "expression", ["sum(p for p, q in items)", "sum(p * max(q, 1) for p, q in items)"]
)
def test_receipt_partial_fixes_fail(
    expression: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "receipt.py").write_text(f"def total(items):\n    return {expression}\n")
    monkeypatch.chdir(tmp_path)
    assert not receipt.verify()


@pytest.mark.parametrize(
    "config,client,override",
    [
        (30, 30, "return value"),
        (15, 30, "return value"),
        (30, 15, "return value"),
        (30, 30, "return 30"),
    ],
)
def test_preflight_defaults_and_overrides(
    config: int,
    client: int,
    override: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "config.py").write_text(f"TIMEOUT_SECONDS = {config}\n")
    source = EDITS["known-preflight"]["client.py"].replace("= 30", f"= {client}")
    (tmp_path / "client.py").write_text(source.replace("return value", override))
    monkeypatch.chdir(tmp_path)
    assert preflight.verify() == (config == 30 and client == 30 and override == "return value")


def accepts_zero(value: int | None) -> int:
    return 30


def test_preflight_requires_zero_rejection() -> None:
    assert not preflight.rejects_zero(accepts_zero)
