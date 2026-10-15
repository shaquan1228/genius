"""Download pinned public benchmark bytes without credentials."""

import gzip
import hashlib
import os
import urllib.request
from pathlib import Path
from tempfile import NamedTemporaryFile


def checked_bytes(path: Path, *, sha256: str) -> bytes:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError(f"Dataset checksum mismatch: {path}")
    return data


def download(*, source: str, sha256: str, destination: Path) -> bytes:
    if destination.exists():
        return checked_bytes(destination, sha256=sha256)
    with urllib.request.urlopen(source, timeout=60) as response:
        data = gzip.decompress(response.read())
    if hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError("Downloaded dataset checksum mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.close()
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return data


def cache_path(sha256: str) -> Path:
    root = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return root / "genius-evals" / f"{sha256}.jsonl"
