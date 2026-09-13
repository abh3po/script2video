"""Image renderer: fit a local image to the canvas with a blurred backdrop."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter

from .base import VisualRenderer
from ..model import Scene


class ImageRenderer(VisualRenderer):
    kind = "image"

    def render(self, scene: Scene, out_dir: Path, duration: float) -> Path:
        src = self.source_path(scene)
        if src is None:
            raise ValueError(f"scene {scene.index}: image visual has no source")
        if not src.exists():
            from .slide import SlideRenderer

            print(f"  ! image not found: {src}; falling back to slide")
            return SlideRenderer(self.cfg).render(scene, out_dir, duration)

        cfg = self.cfg
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / "image.png"

        img = Image.open(src).convert("RGB")
        bg = img.resize((cfg.width, cfg.height))
        bg = bg.filter(ImageFilter.GaussianBlur(40))
        scale = min(cfg.width / img.width, cfg.height / img.height)
        new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
        fg = img.resize(new_size)
        bg.paste(fg, ((cfg.width - new_size[0]) // 2, (cfg.height - new_size[1]) // 2))
        bg.save(out)
        return out
