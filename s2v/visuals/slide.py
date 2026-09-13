"""Text slide renderer (Pillow).

Draws the scene title and subtitle over a solid background with an accent bar.
This is the default, self-contained visual, and doubles as a fallback when an
external asset is missing.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .base import VisualRenderer
from ..model import Scene
from ..parser import strip_markdown


def _hex(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _wrap(draw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if draw.textlength(candidate, font=font) <= max_width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


class SlideRenderer(VisualRenderer):
    kind = "slide"

    def render(self, scene: Scene, out_dir: Path, duration: float) -> Path:
        cfg = self.cfg
        v = cfg.visuals
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / "slide.png"

        img = Image.new("RGB", (cfg.width, cfg.height), _hex(v.background))
        draw = ImageDraw.Draw(img)

        title_font_path = v.title_font or v.font
        try:
            title_font = ImageFont.truetype(title_font_path, v.title_size)
            body_font = ImageFont.truetype(v.font, v.subtitle_size)
        except OSError:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        max_width = cfg.width - 2 * v.margin
        y = v.margin

        accent = _hex(v.accent)
        draw.rectangle([v.margin, y, v.margin + 140, y + 12], fill=accent)
        y += 54

        if scene.title:
            for line in _wrap(draw, strip_markdown(scene.title), title_font, max_width):
                draw.text((v.margin, y), line, font=title_font, fill=_hex(v.foreground))
                y += v.title_size + v.line_spacing

        subtitle = strip_markdown(scene.visual.source or scene.narration or "")
        if subtitle and subtitle != scene.title:
            y += 24
            for line in _wrap(draw, subtitle, body_font, max_width):
                draw.text((v.margin, y), line, font=body_font, fill=_hex(v.foreground))
                y += v.subtitle_size + v.line_spacing
                if y > cfg.height - v.margin:
                    break

        img.save(out)
        return out
