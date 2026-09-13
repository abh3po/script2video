"""Base class and registry for visual renderers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..assets import AssetLibrary
from ..cache import Cache
from ..config import Config
from ..model import Scene


class VisualRenderer(ABC):
    kind = "base"
    #: some renderers (video/Blender/Godot) already produce a timed clip
    produces_clip = False

    def __init__(self, cfg: Config, cache: Cache | None = None, library: AssetLibrary | None = None) -> None:
        self.cfg = cfg
        self.cache = cache or Cache(None)
        self.library = library or AssetLibrary(cfg.assets_dir)

    def source_path(self, scene: Scene) -> Path | None:
        """Resolve a scene's visual source through the asset library."""
        return self.library.resolve(scene.visual.kind, scene.visual.source, scene.visual.params.get("_base_dir"))

    @abstractmethod
    def render(self, scene: Scene, out_dir: Path, duration: float) -> Path:
        """Render *scene* and return the path of the produced asset.

        *duration* is the desired length in seconds. Still renderers may ignore
        it; clip renderers use it to trim/pad.
        """


def get_renderer(kind: str, cfg: Config, cache: Cache | None = None, library: AssetLibrary | None = None) -> VisualRenderer:
    from .blender import BlenderRenderer
    from .godot import GodotRenderer
    from .image import ImageRenderer
    from .slide import SlideRenderer
    from .svg import SvgRenderer
    from .video import VideoRenderer

    table = {
        "slide": SlideRenderer,
        "image": ImageRenderer,
        "svg": SvgRenderer,
        "blender": BlenderRenderer,
        "godot": GodotRenderer,
        "video": VideoRenderer,
    }
    if kind not in table:
        raise ValueError(f"unknown visual kind '{kind}'. choices: {', '.join(table)}")
    return table[kind](cfg, cache=cache, library=library)
