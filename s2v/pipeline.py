"""End-to-end pipeline: script -> scenes -> narration + visuals -> video."""

from __future__ import annotations

from pathlib import Path

import shutil

from .assets import AssetLibrary
from .cache import Cache, file_hash, make_key
from .compose.audio import probe_duration
from .compose.subtitles import write_srt
from .compose.video import build_scene_clip, concatenate, mux_audio_subtitles
from .config import Config
from .model import Scene
from .parser import parse_script
from .tts import get_engine
from .visuals import get_renderer


class Pipeline:
    def __init__(self, config: Config) -> None:
        self.cfg = config
        assets = config.assets_dir if config.assets_dir else None
        self.library = AssetLibrary(assets)
        self.cache = Cache(config.cache_dir, enabled=config.cache)

    # -- individual stages -------------------------------------------------
    def prepare_scenes(self, script: str | Path) -> list[Scene]:
        script = Path(script)
        base_dir = script.parent
        meta, scenes = parse_script(script)
        defaults = meta.get("visual") if isinstance(meta.get("visual"), dict) else {}
        for scene in scenes:
            scene.visual.params.setdefault("_base_dir", str(base_dir))
            if scene.visual.kind == "slide" and not scene.visual.params.get("kind"):
                for key, value in defaults.items():
                    scene.visual.params.setdefault(key, value)
        return scenes

    def synthesize(self, scenes: list[Scene], out_dir: Path) -> None:
        spoken = [s for s in scenes if s.spoken_text()]
        if not spoken:
            return
        engine = get_engine(self.cfg.tts.engine)
        engine_cache = Cache(self.cfg.cache_dir, enabled=self.cfg.cache)
        tts = self.cfg.tts
        print(f"[tts] engine={engine.name} scenes={len(spoken)}")
        for scene in scenes:
            text = scene.spoken_text()
            if not text:
                continue
            scene_dir = out_dir / "scenes" / f"{scene.index:03d}"
            audio_path = scene_dir / "narration.wav"
            overrides = {
                k: v
                for k, v in scene.visual.params.items()
                if k in {"speaker", "language", "instruct", "voice"}
            }
            # cache by engine + all voice settings + exact text
            voice_state = {
                "engine": tts.engine,
                "model": tts.model,
                "speaker": overrides.get("speaker", tts.speaker),
                "voice": overrides.get("voice", tts.voice),
                "language": overrides.get("language", tts.language),
                "instruct": overrides.get("instruct", tts.instruct),
                "ref_audio": self._ref_key(tts.ref_audio),
                "ref_text": tts.ref_text,
            }
            key = make_key("tts", {"voice": voice_state, "text": text})
            cached = engine_cache.lookup("tts", key, ".wav")
            if cached:
                audio_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(cached, audio_path)
                print(f"  - scene {scene.index:03d}: {len(text)} chars (cached)")
            else:
                print(f"  - scene {scene.index:03d}: {len(text)} chars")
                engine.synthesize(text, audio_path, **overrides)
                engine_cache.store("tts", key, lambda staging, src=audio_path: self._copy(src, staging), ".wav")
            scene.audio_path = audio_path
            scene.audio_duration = probe_duration(audio_path)

    @staticmethod
    def _copy(src: Path, staging: Path) -> Path:
        Path(staging).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, staging)
        return Path(staging)

    @staticmethod
    def _ref_key(ref_audio: str | None) -> str | None:
        if not ref_audio:
            return None
        try:
            return file_hash(ref_audio)
        except OSError:
            return ref_audio

    def render_visuals(self, scenes: list[Scene], out_dir: Path) -> None:
        for scene in scenes:
            duration = self._scene_duration(scene)
            renderer = get_renderer(
                scene.visual.kind, self.cfg, cache=self.cache, library=self.library
            )
            scene_dir = out_dir / "scenes" / f"{scene.index:03d}"
            asset = renderer.render(scene, scene_dir, duration)
            if renderer.produces_clip:
                scene.clip_path = asset
            else:
                scene.visual_path = asset

    def _scene_duration(self, scene: Scene) -> float:
        if scene.audio_path and scene.audio_duration > 0:
            scene.duration = scene.audio_duration + self.cfg.pad
        elif "duration" in scene.visual.params:
            scene.duration = float(scene.visual.params["duration"])
        else:
            # rough estimate when there is neither narration nor explicit timing
            scene.duration = max(2.0, 0.35 * len(scene.spoken_text()) + 1.0)
        return scene.duration

    def build(self, script: str | Path, out_dir: str | Path) -> Path:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        cfg = self.cfg

        print(f"[parse] {script}")
        scenes = self.prepare_scenes(script)
        if not scenes:
            raise SystemExit("no scenes found in script")
        print(f"[parse] {len(scenes)} scene(s)")

        self.synthesize(scenes, out_dir)
        for scene in scenes:
            self._scene_duration(scene)
        self.render_visuals(scenes, out_dir)

        print("[compose] building scene clips")
        clips = []
        for scene in scenes:
            scene_dir = out_dir / "scenes" / f"{scene.index:03d}"
            clips.append(build_scene_clip(scene, cfg, scene_dir))

        print("[compose] concatenating")
        stitched = concatenate(clips, cfg, out_dir / "stitched.mp4", out_dir)

        srt_path = None
        if cfg.subtitles:
            srt_path = write_srt(scenes, out_dir / "subtitles.srt")
            print(f"[compose] subtitles -> {srt_path}")

        final = out_dir / "output.mp4"
        print("[compose] muxing final output")
        mux_audio_subtitles(stitched, srt_path, cfg, final)
        print(f"[done] {final}")
        return final
