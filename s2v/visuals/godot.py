"""Godot renderer.

Runs a Godot project and records the viewport with Godot's Movie Maker mode:

    godot --path <project> --resolution <W>x<H> --fixed-fps <fps> \
          --quit-after <frames> --write-movie <dir>/movie.avi

Godot's ``--headless`` mode uses a **dummy** renderer that produces no pixels,
so for real frames the process runs against an X display. On a headless server
this renderer wraps the call in ``xvfb-run`` (override with
``visuals.godot_display``); on a normal desktop the existing ``DISPLAY`` is
used. Results are cached by (project tree content, settings), so a reused
scene/3D model is rendered only once across all videos.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
from pathlib import Path

from .base import VisualRenderer
from ..cache import make_key, hash_files
from ..model import Scene

_SOURCE_EXTS = {".gd", ".tscn", ".tres", ".godot", ".glb", ".gltf", ".fbx", ".obj", ".import", ".png", ".jpg", ".svg"}


class GodotRenderer(VisualRenderer):
    kind = "godot"
    produces_clip = True

    def _binary(self) -> str:
        exe = shutil.which(self.cfg.visuals.godot)
        if not exe:
            raise RuntimeError(
                f"Godot executable '{self.cfg.visuals.godot}' not found. "
                "Install Godot or set visuals.godot to its path."
            )
        return exe

    def _display_prefix(self) -> list[str]:
        """Prefer the running X display, else fall back to Xvfb.

        The virtual screen is made taller/wider than the requested resolution
        so the window manager's decoration does not push the viewport down and
        clip the bottom of the frame.
        """
        mode = self.cfg.visuals.godot_display
        if mode == "none":
            return []
        if os.environ.get("DISPLAY") and mode == "auto":
            return []
        if shutil.which("xvfb-run"):
            w = self.cfg.width + 64
            h = self.cfg.height + 160
            return ["xvfb-run", "-a", "-s", f"-screen 0 {w}x{h}x24"]
        return []

    def render(self, scene: Scene, out_dir: Path, duration: float) -> Path:
        project = self.source_path(scene)
        if project is None or not project.exists():
            raise FileNotFoundError(scene.visual.source or f"scene {scene.index}: no godot project")
        if project.is_file():
            project = project.parent

        cfg = self.cfg
        frames = max(1, math.ceil(duration * cfg.fps)) if duration > 0 else 1
        key = make_key("godot", {
            "project": self._tree_key(project),
            "fps": cfg.fps,
            "w": cfg.width,
            "h": cfg.height,
            "frames": frames,
        })
        suffix = ".mp4"
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "godot.mp4"
        cached = self.cache.lookup("godot", key, suffix)
        if cached:
            shutil.copy2(cached, target)
            return target

        def produce(staging: Path) -> Path:
            work = staging.parent / f"{staging.stem}_work"
            work.mkdir(parents=True, exist_ok=True)
            produced = self._render(project, work, frames)
            produced.replace(staging)
            shutil.rmtree(work, ignore_errors=True)
            return staging

        stored = self.cache.store("godot", key, produce, suffix)
        shutil.copy2(stored, target)
        return target

    def _tree_key(self, project: Path) -> str:
        files = [p for p in project.rglob("*") if p.is_file() and p.suffix.lower() in _SOURCE_EXTS]
        return make_key("tree", hash_files(files))

    def _render(self, project: Path, work: Path, frames: int) -> Path:
        cfg = self.cfg
        movie = work / "movie.avi"
        cmd = self._display_prefix() + [
            self._binary(), "--path", str(project),
            "--resolution", f"{cfg.width}x{cfg.height}",
            "--fixed-fps", str(cfg.fps),
        ]
        if cfg.visuals.godot_renderer:
            cmd += ["--rendering-driver", cfg.visuals.godot_renderer]
        cmd += ["--quit-after", str(frames), "--write-movie", str(movie)]

        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        if not movie.exists() or movie.stat().st_size == 0:
            raise RuntimeError(
                f"Godot produced no movie for {project}. It may need a display: "
                "install xvfb or set visuals.godot_display."
            )

        out = work / "godot.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", "-i", str(movie), "-r", str(cfg.fps),
                "-vf", f"scale={cfg.width}:{cfg.height}:force_original_aspect_ratio=increase,"
                       f"crop={cfg.width}:{cfg.height}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
            ],
            check=True,
        )
        movie.unlink(missing_ok=True)
        return out
