"""Video assembly with ffmpeg."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..config import Config
from ..model import Scene


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def build_scene_clip(scene: Scene, cfg: Config, out_dir: Path) -> Path:
    """Render one scene to ``clip.mp4`` (video + its narration audio).

    If a clip renderer already produced ``scene.clip_path`` it is normalized to
    the target resolution/duration; otherwise the still image is turned into a
    video of the scene duration with a slow zoom.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "clip.mp4"
    fps = cfg.fps
    duration = max(scene.duration, 1.0 / fps)

    if scene.clip_path and Path(scene.clip_path).exists():
        src = Path(scene.clip_path)
        vf = (
            f"scale={cfg.width}:{cfg.height}:force_original_aspect_ratio=increase,"
            f"crop={cfg.width}:{cfg.height},fps={fps},format=yuv420p"
        )
        _run([
            "ffmpeg", "-y", "-v", "error", "-i", str(src), "-t", f"{duration:.3f}",
            "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-an", str(out),
        ])
    else:
        image = Path(scene.visual_path)
        vf = (
            f"scale={cfg.width}:{cfg.height},zoompan=z='min(zoom+0.0004,1.08)'"
            f":d={int(duration * fps)}:s={cfg.width}x{cfg.height}:fps={fps},format=yuv420p"
        )
        _run([
            "ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(image),
            "-t", f"{duration:.3f}", "-vf", vf, "-r", str(fps),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
            "-an", str(out),
        ])

    return _attach_audio(out, scene.audio_path, duration, out_dir)


def _attach_audio(silent_video: Path, audio: Path | None, duration: float, work_dir: Path) -> Path:
    """Replace ``silent_video`` with a version carrying its narration audio."""
    if audio and Path(audio).exists():
        merged = work_dir / "clip_audio.mp4"
        _run([
            "ffmpeg", "-y", "-v", "error", "-i", str(silent_video), "-i", str(audio),
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(merged),
        ])
        merged.replace(silent_video)
        return silent_video

    out = work_dir / "clip_silent.mp4"
    _run([
        "ffmpeg", "-y", "-v", "error", "-i", str(silent_video),
        "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-shortest",
        "-c:v", "copy", "-c:a", "aac", str(out),
    ])
    out.replace(silent_video)
    return silent_video


def concatenate(clips: list[Path], cfg: Config, out_path: Path, work_dir: Path) -> Path:
    """Concatenate scene clips, optionally with a crossfade."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if cfg.crossfade <= 0 or len(clips) == 1:
        listing = work_dir / "concat.txt"
        listing.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
        _run([
            "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
            "-i", str(listing), "-c", "copy", str(out_path),
        ])
        return out_path

    durations = [_probe_video(c) for c in clips]
    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", str(c)]
    filter_parts = []
    v_prev, a_prev = "0:v", "0:a"
    offset = 0.0
    for i in range(1, len(clips)):
        offset += durations[i - 1] - cfg.crossfade
        v_out, a_out = f"v{i}", f"a{i}"
        filter_parts.append(
            f"[{v_prev}][{i}:v]xfade=transition=fade:duration={cfg.crossfade}:"
            f"offset={offset:.3f}[{v_out}]"
        )
        filter_parts.append(f"[{a_prev}][{i}:a]acrossfade=d={cfg.crossfade}[{a_out}]")
        v_prev, a_prev = v_out, a_out

    _run([
        "ffmpeg", "-y", "-v", "error", *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", f"[{v_prev}]", "-map", f"[{a_prev}]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out_path),
    ])
    return out_path


def mux_audio_subtitles(video: Path, srt: Path | None, cfg: Config, out_path: Path) -> Path:
    """Add background music and/or subtitles to the concatenated video.

    Subtitles are added as a soft track (default) or burned in when
    ``cfg.subtitle_burn`` is set. Music is mixed under the narration.
    """
    args = ["ffmpeg", "-y", "-v", "error", "-i", str(video)]
    filter_parts: list[str] = []
    v_map, a_map = "0:v:0", "0:a?"

    music_idx = None
    if cfg.music:
        music_idx = 1
        args += ["-i", cfg.music]

    has_srt = bool(srt and cfg.subtitles)
    srt_idx = 2 if music_idx else 1
    if has_srt:
        args += ["-i", str(srt)]

    # audio: mix music under narration
    if music_idx is not None:
        filter_parts.append(
            f"[{music_idx}:a]volume={cfg.music_volume}[music];"
            f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=0[aout]"
        )
        a_map = "[aout]"

    # video: optionally burn subtitles
    if has_srt and cfg.subtitle_burn:
        escaped = str(srt).replace("\\", "/").replace(":", "\\:")
        if filter_parts:
            # ensure filter_complex handles video too
            filter_parts.append(f"[0:v]subtitles='{escaped}'[vout]")
            v_map = "[vout]"
        else:
            filter_parts.append(f"[0:v]subtitles='{escaped}'[vout]")
            v_map = "[vout]"

    if filter_parts:
        args += ["-filter_complex", ";".join(filter_parts)]
    args += ["-map", v_map, "-map", a_map]

    if has_srt and not cfg.subtitle_burn:
        args += ["-map", f"{srt_idx}:s:0", "-c:s", "mov_text"]

    args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out_path)]
    _run(args)
    return out_path


def _probe_video(path: Path) -> float:
    from .audio import probe_duration

    return probe_duration(path)
