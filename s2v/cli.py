"""Command line interface: ``python -m s2v build script.md``."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .config import Config
from .parser import parse_script
from .pipeline import Pipeline


def _load_config(args) -> Config:
    if args.config:
        cfg = Config.load(args.config)
    else:
        cfg = Config()
    # CLI overrides (only the build subcommand defines all of these)
    overrides = [
        ("width", "width"), ("height", "height"), ("fps", "fps"),
        ("engine", "tts.engine"), ("speaker", "tts.speaker"),
        ("voice", "tts.voice"), ("language", "tts.language"),
        ("music", "music"), ("assets", "assets_dir"), ("cache_dir", "cache_dir"),
    ]
    for arg, attr in overrides:
        value = getattr(args, arg, None)
        if value:
            obj, _, leaf = attr.partition(".")
            setattr(getattr(cfg, obj) if leaf else cfg, leaf or attr, value)
    if getattr(args, "no_subtitles", False):
        cfg.subtitles = False
    if getattr(args, "burn_subtitles", False):
        cfg.subtitle_burn = True
    if getattr(args, "no_cache", False):
        cfg.cache = False
    return cfg


def cmd_build(args) -> int:
    cfg = _load_config(args)
    script = Path(args.script)
    out_dir = Path(args.out) if args.out else Path("build") / script.stem
    final = Pipeline(cfg).build(script, out_dir)
    print(final)
    return 0


def cmd_parse(args) -> int:
    meta, scenes = parse_script(args.script)
    dump = {
        "metadata": meta,
        "scenes": [
            {
                "index": s.index,
                "title": s.title,
                "narration": s.narration,
                "visual": {"kind": s.visual.kind, "source": s.visual.source,
                           "params": {k: v for k, v in s.visual.params.items() if not k.startswith("_")}},
            }
            for s in scenes
        ],
    }
    print(json.dumps(dump, indent=2))
    return 0


def cmd_voices(args) -> int:
    if args.engine != "qwen":
        print("voices listing is only implemented for the qwen engine")
        return 0
    try:
        import torch
        from qwen_tts import Qwen3TTSModel
    except ImportError:
        print("qwen-tts not installed (pip install -U qwen-tts)")
        return 1
    cfg = Config()
    model = Qwen3TTSModel.from_pretrained(
        args.model, device_map=cfg.tts.device, dtype=torch.bfloat16
    )
    print("speakers:", json.dumps(model.get_supported_speakers(), ensure_ascii=False))
    print("languages:", json.dumps(model.get_supported_languages(), ensure_ascii=False))
    return 0


def _resolve_tool(name: str, cfg: Config, attr: str | None = None) -> str | None:
    if attr:
        configured = getattr(cfg.visuals, attr)
        found = shutil.which(configured) or (configured if Path(configured).exists() else None)
        if found:
            return found
    return shutil.which(name)


def cmd_check(args) -> int:
    cfg = _load_config(args)
    bins = ["ffmpeg", "ffprobe"]
    print("required:")
    ok = True
    for b in bins:
        path = shutil.which(b)
        print(f"  {'ok ' if path else 'MISSING'} {b} {path or ''}")
        ok = ok and bool(path)
    print("visual kinds:")
    for name, attr in [("blender", "blender"), ("godot", "godot")]:
        path = _resolve_tool(name, cfg, attr)
        print(f"  {'ok ' if path else '-- '} {name} {path or ''}")
    for t in ["xvfb-run", "rsvg-convert", "inkscape"]:
        path = shutil.which(t)
        print(f"  {'ok ' if path else '-- '} {t} {path or ''}")
    print("tts:")
    for mod, label in [("qwen_tts", "qwen"), ("edge_tts", "edge"), ("piper", "piper")]:
        try:
            __import__(mod)
            print(f"  ok  {label}")
        except ImportError:
            print(f"  --  {label} (pip install)")
    if shutil.which("espeak-ng") or shutil.which("espeak"):
        print("  ok  espeak")
    print("ffmpeg filters:")
    out = __import__("subprocess").run(
        ["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True
    ).stdout
    for f in ["zoompan", "xfade", "acrossfade", "subtitles", "amix"]:
        print(f"  {'ok ' if f in out else '-- '} {f}")
    return 0 if ok else 1


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n} B"


def cmd_assets(args) -> int:
    from .assets import KIND_DIRS, AssetLibrary
    from .cache import Cache

    lib = AssetLibrary(args.assets)
    if args.add:
        kind, _, src = args.add.partition("=")
        dest = lib.add(kind, src, name=args.name)
        print(f"added -> {dest}")
        return 0
    if args.clear_cache:
        Cache(args.cache_dir).clear()
        print("cache cleared")
        return 0
    print(f"library: {lib.root}")
    for kind in KIND_DIRS:
        items = lib.list(kind)
        print(f"  {kind:8} {len(items):3} file(s)")
    cache = Cache(args.cache_dir)
    print(f"cache:   {cache.root} ({_human(cache.size())})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("s2v", description="Turn a script into a video.")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="build a video from a script")
    b.add_argument("script", help="path to the script (markdown/plain text)")
    b.add_argument("-o", "--out", help="output directory")
    b.add_argument("-c", "--config", help="YAML config file")
    b.add_argument("--engine", choices=["qwen", "edge", "piper", "espeak"])
    b.add_argument("--speaker", help="Qwen CustomVoice speaker (e.g. Ryan, Aiden, Vivian)")
    b.add_argument("--voice", help="engine-specific voice id")
    b.add_argument("--language", help="narration language (e.g. English)")
    b.add_argument("--width", type=int)
    b.add_argument("--height", type=int)
    b.add_argument("--fps", type=int)
    b.add_argument("--music", help="background music file")
    b.add_argument("--no-subtitles", action="store_true")
    b.add_argument("--burn-subtitles", action="store_true", help="hard-code captions into the video")
    b.add_argument("--assets", help="shared asset library directory (default: ./assets)")
    b.add_argument("--cache-dir", help="render cache directory (default: ~/.cache/s2v)")
    b.add_argument("--no-cache", action="store_true", help="disable the render cache")
    b.set_defaults(func=cmd_build)

    pa = sub.add_parser("parse", help="parse a script and print the scenes as JSON")
    pa.add_argument("script")
    pa.set_defaults(func=cmd_parse)

    v = sub.add_parser("voices", help="list Qwen speakers/languages")
    v.add_argument("--engine", default="qwen")
    v.add_argument("--model", default="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
    v.set_defaults(func=cmd_voices)

    c = sub.add_parser("check", help="check external dependencies")
    c.add_argument("-c", "--config", help="YAML config file (to locate configured tool paths)")
    c.set_defaults(func=cmd_check)

    a = sub.add_parser("assets", help="inspect the shared asset library and render cache")
    a.add_argument("--assets", default="assets", help="asset library directory")
    a.add_argument("--cache-dir", default="~/.cache/s2v", help="render cache directory")
    a.add_argument("--add", metavar="KIND=PATH", help="copy an asset into the library")
    a.add_argument("--name", help="name to store the added asset under")
    a.add_argument("--clear-cache", action="store_true", help="delete the render cache")
    a.set_defaults(func=cmd_assets)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # surface a clean error
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
