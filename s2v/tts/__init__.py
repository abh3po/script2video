"""TTS engine registry."""

from __future__ import annotations

from .base import TTSEngine
from .qwen import QwenTTSEngine

ENGINES = {
    "qwen": QwenTTSEngine,
    "edge": "s2v.tts.edge:EdgeTTSEngine",
    "piper": "s2v.tts.piper:PiperTTSEngine",
    "espeak": "s2v.tts.espeak:EspeakTTSEngine",
}


def get_engine(name: str) -> TTSEngine:
    if name not in ENGINES:
        raise ValueError(f"unknown TTS engine '{name}'. choices: {', '.join(ENGINES)}")
    target = ENGINES[name]
    if isinstance(target, str):
        module_name, cls_name = target.split(":")
        import importlib

        target = getattr(importlib.import_module(module_name), cls_name)
    return target()


__all__ = ["TTSEngine", "QwenTTSEngine", "get_engine", "ENGINES"]
