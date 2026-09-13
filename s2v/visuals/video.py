"""Video renderer: use a local video file, trimmed/padded to the scene length."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .base import VisualRenderer
from ..model import Scene


class VideoRenderer(VisualRenderer):
    kind = "video"
    produces_clip = True

    def render(self, scene: Scene, out_dir: Path, duration: float) -> Path:
        src = self.source_path(scene)
        if src is None:
            raise ValueError(f"scene {scene.index}: video visual has no source")
        if not src.exists():
            raise FileNotFoundError(src)

        cfg = self.cfg
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / "video.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-stream_loop", "-1", "-i", str(src),
                "-t", f"{duration:.3f}",
                "-vf", f"scale={cfg.width}:{cfg.height}:force_original_aspect_ratio=increase,"
                       f"crop={cfg.width}:{cfg.height},fps={cfg.fps}",
                "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
            ],
            check=True,
        )
        return out
