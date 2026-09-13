"""Blender renderer.

Renders a ``.blend`` file's animation to a clip:

    blender -b scene.blend --python-expr "<set fps/frame_end>" -o <dir>/f_ -F PNG -a
    ffmpeg -framerate <fps> -i <dir>/f_%04d.png -> scene.mp4

Results are cached by (blend file content, render settings), so the same 3D
model / camera move is rendered **once** and reused across every scene and every
video that requests it.
"""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

from .base import VisualRenderer
from ..cache import file_hash, make_key
from ..model import Scene


class BlenderRenderer(VisualRenderer):
    kind = "blender"
    produces_clip = True

    def _binary(self) -> str:
        exe = shutil.which(self.cfg.visuals.blender)
        if not exe:
            raise RuntimeError(
                f"Blender executable '{self.cfg.visuals.blender}' not found. "
                "Install Blender or set visuals.blender to its path."
            )
        return exe

    def render(self, scene: Scene, out_dir: Path, duration: float) -> Path:
        blend = self.source_path(scene)
        if not blend or not blend.exists():
            raise FileNotFoundError(
                scene.visual.source or f"scene {scene.index}: blender visual has no .blend source"
            )

        cfg = self.cfg
        samples = scene.visual.params.get("samples", cfg.visuals.blender_samples)
        # key on file content + settings that change the pixels
        key = make_key("blender", {
            "blend": file_hash(blend),
            "fps": cfg.fps,
            "w": cfg.width,
            "h": cfg.height,
            "seconds": round(duration, 3),
            "samples": samples,
        })
        suffix = ".mp4"
        cached = self.cache.lookup("blender", key, suffix)
        if cached:
            out_dir.mkdir(parents=True, exist_ok=True)
            target = out_dir / "blender.mp4"
            shutil.copy2(cached, target)
            return target

        out_dir.mkdir(parents=True, exist_ok=True)

        def produce(staging: Path) -> Path:
            work = staging.parent / f"{staging.stem}_work"
            produced = self._render(blend, work, duration)
            produced.replace(staging)
            shutil.rmtree(work, ignore_errors=True)
            return staging

        stored = self.cache.store("blender", key, produce, suffix)
        target = out_dir / "blender.mp4"
        shutil.copy2(stored, target)
        return target

    def _render(self, blend: Path, work: Path, duration: float) -> Path:
        cfg = self.cfg
        frames_dir = work / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        frames = max(1, math.ceil(duration * cfg.fps)) if duration > 0 else 1
        expr = (
            "import bpy;"
            "s=bpy.context.scene;"
            f"s.render.fps={cfg.fps};"
            "s.render.image_settings.file_format='PNG';"
            f"s.frame_start=1;s.frame_end={frames}"
        )
        subprocess.run(
            [
                self._binary(), "-b", str(blend),
                "--python-expr", expr,
                "-o", str(frames_dir / "f_"), "-F", "PNG", "-a",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )

        rendered = sorted(frames_dir.glob("f_*.png"))
        if not rendered:
            raise RuntimeError(f"Blender produced no frames for {blend}")

        out = work / "blender.mp4"
        scale = (
            f"scale={cfg.width}:{cfg.height}:force_original_aspect_ratio=increase,"
            f"crop={cfg.width}:{cfg.height}"
        )
        if len(rendered) == 1:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(rendered[0]),
                    "-t", f"{max(duration, 1 / cfg.fps):.3f}", "-r", str(cfg.fps),
                    "-vf", scale, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
                ],
                check=True,
            )
        else:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error", "-framerate", str(cfg.fps),
                    "-i", str(frames_dir / "f_%04d.png"), "-r", str(cfg.fps),
                    "-vf", scale, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
                ],
                check=True,
            )
        return out
