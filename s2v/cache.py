"""Content-addressed render cache.

Expensive artifacts (TTS audio, rendered Blender/Godot clips, rasterised
slides) are cached under ``cache_dir`` and keyed by a hash of everything that
affects the result. Identical work across scenes and across *different videos*
is then reused for free. 3D model renders, which are the slowest, benefit most.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Iterable


def file_hash(path: str | Path, chunk: int = 1 << 20) -> str:
    """Streaming sha256 of a file, or a marker for a directory tree."""
    path = Path(path)
    h = hashlib.sha256()
    if path.is_dir():
        for child in sorted(p for p in path.rglob("*") if p.is_file()):
            h.update(str(child.relative_to(path)).encode())
            h.update(file_hash(child).encode())
        return h.hexdigest()
    if not path.exists():
        return f"missing:{path}"
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def make_key(namespace: str, payload: dict) -> str:
    blob = json.dumps({"ns": namespace, "p": payload}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


class Cache:
    def __init__(self, root: str | Path | None, enabled: bool = True) -> None:
        self.root = Path(root).expanduser() if root else None
        self.enabled = bool(enabled and self.root)

    # -- lookup / storage --------------------------------------------------
    def _slot(self, namespace: str, key: str, suffix: str) -> Path:
        assert self.root is not None
        return self.root / namespace / key[:2] / f"{key}{suffix}"

    def lookup(self, namespace: str, key: str, suffix: str) -> Path | None:
        if not self.enabled:
            return None
        slot = self._slot(namespace, key, suffix)
        return slot if slot.exists() else None

    def store(self, namespace: str, key: str, producer: Callable[[Path], Path], suffix: str) -> Path:
        """Return a cached artifact, producing it atomically on a miss."""
        if not self.enabled:
            tmp_dir = Path(tempfile.mkdtemp(prefix="s2v-"))
            produced = Path(producer(tmp_dir / f"out{suffix}"))
            return produced

        slot = self._slot(namespace, key, suffix)
        if slot.exists():
            return slot

        slot.parent.mkdir(parents=True, exist_ok=True)
        staging = slot.with_suffix(slot.suffix + f".tmp{os.getpid()}")
        produced = Path(producer(staging))
        # producer may write a different suffix than staging; normalise
        if produced != staging and produced.exists():
            produced.replace(staging)
        staging.replace(slot)
        return slot

    def clear(self) -> None:
        if self.enabled and self.root and self.root.exists():
            shutil.rmtree(self.root)

    def size(self) -> int:
        if not (self.enabled and self.root and self.root.exists()):
            return 0
        return sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())


def hash_files(paths: Iterable[str | Path]) -> dict[str, str]:
    return {str(p): file_hash(p) for p in paths}
