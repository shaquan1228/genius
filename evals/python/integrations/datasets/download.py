"""Pinned downloads with checksum verification and atomic cache publication."""

import gzip
import hashlib
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile


@dataclass(frozen=True, kw_only=True)
class Download:
    source: str
    sha256: str
    destination: Path


def cache_path(sha256: str) -> Path:
    root = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return root / "genius-evals" / f"{sha256}.jsonl"


def download(*, request: Download) -> bytes:
    if request.destination.exists():
        data = request.destination.read_bytes()
    else:
        with urllib.request.urlopen(request.source, timeout=60) as response:
            data = gzip.decompress(response.read())
    if hashlib.sha256(data).hexdigest() != request.sha256:
        raise ValueError("Dataset checksum mismatch")
    if not request.destination.exists():
        request.destination.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=request.destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(data)
                stream.close()
                temporary.replace(request.destination)
            finally:
                temporary.unlink(missing_ok=True)
    return data
