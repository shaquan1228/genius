"""Pinned downloads verify cached bytes and publish complete files atomically."""

import gzip
import hashlib
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from kernel import Outcome, Verification

from evals.python import datasets
from evals.python.datasets.humanevalplus import _cache_path, _download

DATA = b'{"task_id":"HumanEval/0"}\n'
DIGEST = hashlib.sha256(DATA).hexdigest()


def download_and_cache(tmp_path: Path) -> None:
    destination = tmp_path / "nested/dataset.jsonl"
    with patch("urllib.request.urlopen", return_value=BytesIO(gzip.compress(DATA))) as request:
        assert (
            _download(source="https://example.test/data.gz", sha256=DIGEST, destination=destination)
            == DATA
        )
        assert _download(source="unused", sha256=DIGEST, destination=destination) == DATA
    request.assert_called_once_with("https://example.test/data.gz", timeout=60)
    assert list(destination.parent.iterdir()) == [destination]


def corrupt_cache_is_not_redownloaded(tmp_path: Path) -> None:
    path = tmp_path / "cache"
    path.write_bytes(b"wrong")
    with patch("urllib.request.urlopen") as request, pytest.raises(ValueError, match="checksum"):
        _download(source="unused", sha256=DIGEST, destination=path)
    request.assert_not_called()


def corrupt_download_not_published(tmp_path: Path) -> None:
    path = tmp_path / "cache"
    with (
        patch("urllib.request.urlopen", return_value=BytesIO(gzip.compress(b"bad"))),
        pytest.raises(ValueError, match="checksum"),
    ):
        _download(source="url", sha256=DIGEST, destination=path)
    assert not path.exists()


def failed_atomic_publish_cleans_temporary_file(tmp_path: Path) -> None:
    with (
        patch("urllib.request.urlopen", return_value=BytesIO(gzip.compress(DATA))),
        patch.object(Path, "replace", side_effect=OSError("disk")),
        pytest.raises(OSError, match="disk"),
    ):
        _download(source="url", sha256=DIGEST, destination=tmp_path / "data")
    assert list(tmp_path.iterdir()) == []


def cache_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", "/tmp/benchmark-cache")
    assert _cache_path("abc") == Path("/tmp/benchmark-cache/genius-evals/abc.jsonl")
    monkeypatch.delenv("XDG_CACHE_HOME")
    assert _cache_path("abc") == Path.home() / ".cache/genius-evals/abc.jsonl"


def clear_compiled_cache_preserves_live_snapshots() -> None:
    before = datasets.load_dataset()
    datasets.clear_cache()
    after = datasets.load_dataset()
    assert after is not before
    assert tuple(before.cases) == tuple(after.cases)


@pytest.mark.parametrize(
    ("case_id", "suite_passed"),
    [("completion-verified", True), ("completion-all-skipped", False)],
)
def reasoning_gate_fixtures_and_claims(case_id: str, *, suite_passed: bool) -> None:
    dataset = datasets.load_dataset(selection="reasoning_gate")
    declaration = dataset.records[case_id]
    assert declaration.skill == "reasoning"
    task = declaration.task
    assert "checks_test.py" in {file.path for file in task.fixture}
    assert not task.allowed_files
    for claim in (suite_passed, not suite_passed):
        outcome = Outcome(
            changed_files=[],
            verification=Verification.Unchecked(),
            response={"suite_passed": claim, "reason": "The current suite supplied the evidence."},
            facts=[],
        )
        assert dict(task.grade(outcome=outcome))["correctness"] == (claim == suite_passed)
