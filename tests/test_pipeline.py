"""Smoke tests that need only ffmpeg (no TTS, no Blender/Godot).

Run with:  python -m pytest -q     or    python tests/test_pipeline.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from s2v.compose.audio import probe_duration  # noqa: E402
from s2v.compose.subtitles import assemble_srt, format_timestamp  # noqa: E402
from s2v.config import Config  # noqa: E402
from s2v.parser import parse_script, strip_markdown  # noqa: E402
from s2v.pipeline import Pipeline  # noqa: E402


def test_timestamp():
    assert format_timestamp(0) == "00:00:00,000"
    assert format_timestamp(3661.5) == "01:01:01,500"


def test_parser_scenes(tmp=tempfile.mkdtemp()):
    script = Path(tmp) / "s.md"
    script.write_text(
        "# ignored title\n\n"
        "## One\n\nHello **world**.\n\n"
        "<!-- visual: slide | Slide one -->\n\n"
        "## Two\n\n<!-- duration: 3 -->\n"
    )
    meta, scenes = parse_script(script)
    titles = [s.title for s in scenes]
    assert titles == ["One", "Two"], titles
    assert scenes[0].narration == "Hello world."
    assert scenes[0].visual.kind == "slide"
    assert scenes[1].visual.params.get("duration") == 3.0


def test_strip_markdown():
    assert strip_markdown("**bold** and _em_ and `code`") == "bold and em and code"


def test_silent_build():
    """A script with no narration (timed slides) builds end to end, no audio."""
    tmp = Path(tempfile.mkdtemp())
    script = tmp / "silent.md"
    script.write_text(
        "## First\n\n<!-- duration: 2 -->\n\n"
        "## Second\n\n<!-- duration: 2 -->\n"
    )
    cfg = Config()
    cfg.width, cfg.height, cfg.fps = 320, 180, 12
    cfg.subtitles = False
    cfg.cache = False
    cfg.assets_dir = str(tmp / "assets")
    out = Pipeline(cfg).build(script, tmp / "build")
    assert out.exists() and out.stat().st_size > 0
    # the muxed output should carry an audio stream (silence) and video
    streams = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
         "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "video" in streams and "audio" in streams
    assert probe_duration(out) > 3.5


def test_srt_generation():
    script = Path(tempfile.mkdtemp()) / "s.md"
    script.write_text("## T\n\nOne. Two. Three.\n")
    _, scenes = parse_script(script)
    scenes[0].duration = 6.0
    srt = assemble_srt(scenes)
    assert "-->" in srt and "One." in srt and "Three." in srt


def _main() -> int:
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
