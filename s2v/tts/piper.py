"""piper engine: fast, fully offline neural TTS.

Install::

    pip install -U piper-tts

Requires a voice model, e.g. ``en_US-lessac-medium.onnx`` (download from the
rhasspy/piper-voices repo) plus its ``.onnx.json`` metadata file.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .base import TTSEngine


class PiperTTSEngine(TTSEngine):
    name = "piper"

    def synthesize(self, text: str, out_path: Path, **overrides) -> Path:
        model = overrides.get("piper_model", self.cfg.piper_model)
        if not model:
            raise RuntimeError("piper needs tts.piper_model set to a .onnx voice path")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            from piper import PiperVoice  # type: ignore

            voice = PiperVoice.load(model)
            with open(out_path, "wb") as fh:
                voice.synthesize(text, fh)
        except ImportError:
            subprocess.run(
                ["piper", "--model", model, "--output_file", str(out_path)],
                input=text.encode(),
                check=True,
            )
        return self._normalize(out_path)
