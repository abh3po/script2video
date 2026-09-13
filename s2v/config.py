"""Configuration for the s2v pipeline.

A run config is a small YAML/JSON document:

    width: 1920
    height: 1080
    fps: 30
    pad: 0.4                # silence (s) appended to each narration clip
    crossfade: 0.0          # seconds of overlap between scenes
    subtitles: true
    music: null             # optional background music file
    music_volume: 0.15
    tts:
      engine: qwen          # qwen | edge | piper | espeak
      model: Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice
      speaker: Ryan
      language: English
      instruct: null
      device: cuda:0
      attn: flash_attention_2
    visuals:
      default_kind: slide
      background: "#101418"
      foreground: "#f5f7fa"
      accent: "#4cc9f0"
      font: /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TTSConfig:
    engine: str = "qwen"
    model: str = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
    speaker: str = "Ryan"
    language: str = "English"
    instruct: str | None = None
    device: str = "cuda:0"
    attn: str = "flash_attention_2"
    # voice cloning fields (Base model)
    ref_audio: str | None = None
    ref_text: str | None = None
    # edge-tts voice name
    voice: str = "en-US-GuyNeural"
    # piper model path
    piper_model: str | None = None


@dataclass
class VisualConfig:
    default_kind: str = "slide"
    background: str = "#101418"
    foreground: str = "#f5f7fa"
    accent: str = "#4cc9f0"
    font: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    title_font: str | None = None
    subtitle_size: int = 46
    title_size: int = 78
    margin: int = 90
    line_spacing: int = 14
    blender: str = "blender"
    godot: str = "godot"
    blender_samples: int = 64
    #: Godot display handling: auto (use DISPLAY, else xvfb-run), xvfb, or none
    godot_display: str = "auto"
    #: optional Godot rendering driver. Vulkan works with the GPU via Xvfb and
    #: gives exact-size frames; use "opengl3" only if Vulkan is unavailable.
    godot_renderer: str | None = "vulkan"


@dataclass
class Config:
    width: int = 1920
    height: int = 1080
    fps: int = 30
    pad: float = 0.4
    crossfade: float = 0.0
    subtitles: bool = True
    subtitle_burn: bool = False
    music: str | None = None
    music_volume: float = 0.15
    #: shared library of reusable assets (models, textures, audio, svg, ...)
    assets_dir: str = "assets"
    #: content-addressed cache of expensive renders (set to null to disable)
    cache_dir: str | None = "~/.cache/s2v"
    cache: bool = True
    tts: TTSConfig = field(default_factory=TTSConfig)
    visuals: VisualConfig = field(default_factory=VisualConfig)
    #: directory of the config file, used to resolve relative paths
    base_dir: str | None = None

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        path = Path(path)
        raw = yaml.safe_load(path.read_text()) or {}
        tts = TTSConfig(**{k: v for k, v in raw.pop("tts", {}).items() if k in TTSConfig.__dataclass_fields__})
        visuals = VisualConfig(
            **{k: v for k, v in raw.pop("visuals", {}).items() if k in VisualConfig.__dataclass_fields__}
        )
        cfg = cls(
            **{k: v for k, v in raw.items() if k in cls.__dataclass_fields__},
            tts=tts,
            visuals=visuals,
        )
        # resolve relative paths against the config file directory
        base = path.parent
        cfg.base_dir = str(base)
        if cfg.music:
            cfg.music = str((base / cfg.music).resolve()) if not Path(cfg.music).is_absolute() else cfg.music
        if cfg.assets_dir and not Path(cfg.assets_dir).is_absolute():
            cfg.assets_dir = str((base / cfg.assets_dir).resolve())
        return cfg
