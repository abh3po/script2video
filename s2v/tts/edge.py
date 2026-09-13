"""edge-tts engine: free Microsoft neural voices over the network.

Install::

    pip install -U edge-tts
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from .base import TTSEngine


class EdgeTTSEngine(TTSEngine):
    name = "edge"

    def synthesize(self, text: str, out_path: Path, **overrides) -> Path:
        try:
            import edge_tts
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("edge-tts is not installed. Run: pip install -U edge-tts") from exc

        voice = overrides.get("voice", self.cfg.voice)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_suffix(".mp3")

        async def _run() -> None:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(tmp))

        asyncio.run(_run())
        # transcode mp3 -> wav
        import subprocess

        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(tmp), str(out_path)], check=True
        )
        tmp.unlink(missing_ok=True)
        return self._normalize(out_path)
