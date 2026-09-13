"""Qwen3-TTS engine (local GPU via the ``qwen-tts`` package).

Install::

    pip install -U qwen-tts

Supports the three released model families:

  * ``Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`` - fixed premium speakers
  * ``Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign`` - voice described in natural language
  * ``Qwen/Qwen3-TTS-12Hz-1.7B-Base``        - 3s voice cloning
"""

from __future__ import annotations

from pathlib import Path

from .base import TTSEngine


class QwenTTSEngine(TTSEngine):
    name = "qwen"

    def __init__(self, cfg=None) -> None:
        super().__init__(cfg)
        self._model = None
        self._voice_clone_prompt = None

    # -- model loading -----------------------------------------------------
    def _load(self):
        if self._model is not None:
            return self._model
        try:
            import torch
            from qwen_tts import Qwen3TTSModel
        except ImportError as exc:  # pragma: no cover - depends on env
            raise RuntimeError(
                "qwen-tts is not installed. Run: pip install -U qwen-tts"
            ) from exc

        kwargs = dict(device_map=self.cfg.device, dtype=torch.bfloat16)
        if self.cfg.attn:
            kwargs["attn_implementation"] = self.cfg.attn
        self._model = Qwen3TTSModel.from_pretrained(self.cfg.model, **kwargs)
        return self._model

    def _mode(self) -> str:
        model = self.cfg.model.lower()
        if "voicedesign" in model or "voice_design" in model or "voice-design" in model:
            return "design"
        if "customvoice" in model or "custom-voice" in model:
            return "custom"
        return "clone"

    # -- synthesis ---------------------------------------------------------
    def synthesize(self, text: str, out_path: Path, **overrides) -> Path:
        import soundfile as sf

        model = self._load()
        language = overrides.get("language", self.cfg.language)
        instruct = overrides.get("instruct", self.cfg.instruct)
        speaker = overrides.get("speaker", self.cfg.speaker)
        mode = self._mode()

        if mode == "custom":
            kwargs = dict(text=text, language=language, speaker=speaker)
            if instruct:
                kwargs["instruct"] = instruct
            wavs, sr = model.generate_custom_voice(**kwargs)
        elif mode == "design":
            wavs, sr = model.generate_voice_design(
                text=text, language=language, instruct=instruct or ""
            )
        else:
            if self._voice_clone_prompt is None:
                ref_audio = overrides.get("ref_audio", self.cfg.ref_audio)
                ref_text = overrides.get("ref_text", self.cfg.ref_text)
                if not ref_audio:
                    raise RuntimeError(
                        "Qwen Base model needs tts.ref_audio (and ideally tts.ref_text) to clone a voice."
                    )
                self._voice_clone_prompt = model.create_voice_clone_prompt(
                    ref_audio=ref_audio, ref_text=ref_text, x_vector_only_mode=not ref_text
                )
            wavs, sr = model.generate_voice_clone(
                text=text, language=language, voice_clone_prompt=self._voice_clone_prompt
            )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), wavs[0], sr)
        return self._normalize(out_path)
