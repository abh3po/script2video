"""Base class for TTS engines."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from ..config import TTSConfig


class TTSEngine(ABC):
    """Synthesize narration text to a WAV file."""

    name = "base"

    def __init__(self, cfg: TTSConfig | None = None) -> None:
        self.cfg = cfg or TTSConfig()

    @abstractmethod
    def synthesize(self, text: str, out_path: Path, **overrides) -> Path:
        """Write speech for *text* to *out_path* and return it."""

    @staticmethod
    def _normalize(out_path: Path) -> Path:
        """Ensure a standard PCM WAV the rest of the pipeline can consume."""
        tmp = out_path.with_suffix(".raw.wav")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", "-i", str(out_path),
                "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(tmp),
            ],
            check=True,
        )
        tmp.replace(out_path)
        return out_path
