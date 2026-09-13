"""Audio helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def probe_duration(path: str | Path) -> float:
    """Return the duration of a media file in seconds (0.0 on failure)."""
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "json", str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return float(json.loads(out.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def has_audio(path: str | Path) -> bool:
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "a",
                "-show_entries", "stream=index", "-of", "csv=p=0", str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return bool(out.stdout.strip())
    except Exception:
        return False
