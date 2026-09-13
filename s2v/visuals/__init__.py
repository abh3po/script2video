"""Visual renderers: turn a :class:`~s2v.model.Visual` into a still image or clip."""

from __future__ import annotations

from .base import VisualRenderer, get_renderer
from .slide import SlideRenderer
from .image import ImageRenderer
from .svg import SvgRenderer
from .blender import BlenderRenderer
from .godot import GodotRenderer
from .video import VideoRenderer

__all__ = [
    "VisualRenderer",
    "get_renderer",
    "SlideRenderer",
    "ImageRenderer",
    "SvgRenderer",
    "BlenderRenderer",
    "GodotRenderer",
    "VideoRenderer",
]
