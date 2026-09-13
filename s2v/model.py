"""Data model shared across the pipeline.

A script is a list of :class:`Scene`. Each scene carries narration text, an
optional visual spec, and the paths of the artifacts produced for it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

SLIDE = "slide"
IMAGE = "image"
SVG = "svg"
BLENDER = "blender"
GODOT = "godot"
VIDEO = "video"

VISUAL_KINDS = {SLIDE, IMAGE, SVG, BLENDER, GODOT, VIDEO}


@dataclass
class Visual:
    """How to draw a scene's picture.

    kind: one of ``slide``, ``image``, ``svg``, ``blender``, ``godot``, ``video``.
    source: path or identifier. Interpreted per kind:

      * slide   -> subtitle / heading text (falls back to narration)
      * image   -> local image file
      * svg     -> local SVG file
      * blender -> ``.blend`` file path
      * godot   -> project dir (or a scene path)
      * video   -> local video file
    """

    kind: str = SLIDE
    source: Optional[str] = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Scene:
    index: int
    title: Optional[str] = None
    narration: str = ""
    visual: Visual = field(default_factory=Visual)
    # artifacts populated by the pipeline
    audio_path: Optional[Path] = None
    audio_duration: float = 0.0
    visual_path: Optional[Path] = None
    clip_path: Optional[Path] = None
    duration: float = 0.0
    word_timings: list[dict[str, Any]] = field(default_factory=list)

    def spoken_text(self) -> str:
        """The text to narrate.

        Only body text is spoken. A slide's label/title is shown on screen but
        is never read aloud; write the line as narration if you want it voiced.
        This keeps title cards and timed slides silent.
        """
        return self.narration.strip()
