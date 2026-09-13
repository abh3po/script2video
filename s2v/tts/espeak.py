"""espeak-ng engine: offline, always available, robotic. Good for drafts."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import TTSEngine


class EspeakTTSEngine(TTSEngine):
    name = "espeak"

    def synthesize(self, text: str, out_path: Path, **overrides) -> Path:
        exe = shutil.which("espeak-ng") or shutil.which("espeak")
        if not exe:
            raise RuntimeError("espeak-ng/espeak not found on PATH")
        voice = overrides.get("voice", self.cfg.voice)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [exe, "-v", voice, "-w", str(out_path), "--stdin"],
            input=text.encode(),
            check=True,
        )
        return self._normalize(out_path)
