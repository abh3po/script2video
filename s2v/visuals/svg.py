"""SVG renderer: rasterize an SVG (rsvg-convert / inkscape / cairosvg) then fit."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import VisualRenderer
from ..model import Scene


class SvgRenderer(VisualRenderer):
    kind = "svg"

    def render(self, scene: Scene, out_dir: Path, duration: float) -> Path:
        src = self.source_path(scene)
        if src is None:
            raise ValueError(f"scene {scene.index}: svg visual has no source")
        if not src.exists():
            from .slide import SlideRenderer

            print(f"  ! svg not found: {src}; falling back to slide")
            return SlideRenderer(self.cfg).render(scene, out_dir, duration)

        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / "svg.png"
        w, h = self.cfg.width, self.cfg.height

        if shutil.which("rsvg-convert"):
            subprocess.run(
                ["rsvg-convert", "-w", str(w), "-h", str(h), "-b", "white", "-o", str(out), str(src)],
                check=True,
            )
        elif shutil.which("inkscape"):
            subprocess.run(
                ["inkscape", str(src), "-w", str(w), "-h", str(h), "-o", str(out)],
                check=True,
            )
        else:
            try:
                import cairosvg

                cairosvg.svg2png(url=str(src), write_to=str(out), output_width=w, output_height=h)
            except ImportError as exc:
                raise RuntimeError(
                    "no SVG rasterizer found. Install one of: rsvg-convert, inkscape, cairosvg"
                ) from exc

        return out
