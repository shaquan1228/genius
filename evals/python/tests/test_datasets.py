"""Pinned downloads verify cached bytes and publish complete files atomically."""

import gzip
import hashlib
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest

from evals.python.datasets import cache_path, checked_bytes, download

DATA = b'{"task_id":"HumanEval/0"}\n'
DIGEST = hashlib.sha256(DATA).hexdigest()


def test_download_and_cache(tmp_path: Path) -> None:
    destination = tmp_path / "nested/dataset.jsonl"
    with patch("urllib.request.urlopen", return_value=BytesIO(gzip.compress(DATA))) as request:
        assert (
            download(source="https://example.test/data.gz", sha256=DIGEST, destination=destination)
            == DATA
        )
        assert download(source="unused", sha256=DIGEST, destination=destination) == DATA
    request.assert_called_once_with("https://example.test/data.gz", timeout=60)
    assert list(destination.parent.iterdir()) == [destination]


def test_corrupt_cache_is_not_redownloaded(tmp_path: Path) -> None:
    path = tmp_path / "cache"
    path.write_bytes(b"wrong")
    with patch("urllib.request.urlopen") as request, pytest.raises(ValueError, match="checksum"):
        download(source="unused", sha256=DIGEST, destination=path)
    request.assert_not_called()
    with pytest.raises(ValueError, match="checksum"):
        checked_bytes(path, sha256=DIGEST)


def test_corrupt_download_not_published(tmp_path: Path) -> None:
    path = tmp_path / "cache"
    with (
        patch("urllib.request.urlopen", return_value=BytesIO(gzip.compress(b"bad"))),
        pytest.raises(ValueError, match="checksum"),
    ):
        download(source="url", sha256=DIGEST, destination=path)
    assert not path.exists()


def test_failed_atomic_publish_cleans_temporary_file(tmp_path: Path) -> None:
    with (
        patch("urllib.request.urlopen", return_value=BytesIO(gzip.compress(DATA))),
        patch.object(Path, "replace", side_effect=OSError("disk")),
        pytest.raises(OSError, match="disk"),
    ):
        download(source="url", sha256=DIGEST, destination=tmp_path / "data")
    assert list(tmp_path.iterdir()) == []


def test_cache_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", "/tmp/benchmark-cache")
    assert cache_path("abc") == Path("/tmp/benchmark-cache/genius-evals/abc.jsonl")
    monkeypatch.delenv("XDG_CACHE_HOME")
    assert cache_path("abc") == Path.home() / ".cache/genius-evals/abc.jsonl"
