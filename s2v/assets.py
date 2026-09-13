"""Shared, reusable asset library.

Assets are stored once on disk and referenced by scripts, so expensive 3D
models, meshes, textures, music and reference audio are reused across videos
instead of being copied per build.

Layout (``assets_dir``, default ``./assets``)::

    assets/
      models/        .blend files, .glb/.gltf, .fbx
      textures/      images used by materials
      audio/         music beds, cloned-voice reference clips
      svg/           vector art
      images/        generic stills
      fonts/

A script can refer to an asset by name, and s2v resolves it against this tree:

    <!-- visual: blender | atom -->          -> assets/models/atom.blend
    <!-- visual: image   | diagram.png -->   -> assets/images/diagram.png
    <!-- visual: svg     | atom.svg -->      -> assets/svg/atom.svg

Absolute paths and project-relative paths still work unchanged.
"""

from __future__ import annotations

from pathlib import Path

#: directory name (inside the library) consulted for each visual kind
KIND_DIRS = {
    "blender": ["models"],
    "godot": ["models", "godot"],
    "image": ["images", "textures"],
    "svg": ["svg"],
    "video": ["video", "clips"],
    "music": ["audio"],
    "ref_audio": ["audio"],
}

EXTENSIONS = {
    "blender": [".blend"],
    "godot": ["", ".godot", ".tscn"],
    "image": [".png", ".jpg", ".jpeg", ".webp", ".bmp"],
    "svg": [".svg"],
    "video": [".mp4", ".mov", ".mkv", ".webm"],
    "music": [".mp3", ".wav", ".m4a", ".flac", ".ogg"],
    "ref_audio": [".wav", ".mp3", ".flac", ".m4a", ".ogg"],
}


class AssetLibrary:
    def __init__(self, root: str | Path | None) -> None:
        self.root = Path(root).expanduser().resolve() if root else None

    def resolve(self, kind: str, source: str | None, base_dir: str | Path | None = None) -> Path | None:
        """Resolve *source* for a visual/tool *kind*.

        Order: absolute path, then ``base_dir`` (the script's folder), then the
        shared library. Returns ``None`` for empty sources.
        """
        if not source:
            return None
        raw = Path(source).expanduser()
        if raw.is_absolute():
            return raw
        if base_dir:
            candidate = Path(base_dir) / raw
            if candidate.exists():
                return candidate
        return self.find(kind, source) or Path(base_dir or ".") / raw

    def find(self, kind: str, name: str) -> Path | None:
        """Search the library for *name* (adds known extensions)."""
        if not (self.root and self.root.exists()):
            return None
        dirs = KIND_DIRS.get(kind, [kind])
        exts = EXTENSIONS.get(kind, [""])
        name_path = Path(name)
        wanted = [name_path] if name_path.suffix else [name_path.with_suffix(e) for e in exts]
        for d in dirs:
            for candidate in wanted:
                p = self.root / d / candidate
                if p.exists():
                    return p
        # fall back to a recursive search for the bare filename
        for d in dirs:
            base = self.root / d
            if not base.exists():
                continue
            for p in base.rglob(name_path.name):
                if p.is_file():
                    return p
        return None

    def add(self, kind: str, src: str | Path, name: str | None = None) -> Path:
        """Copy an asset into the library and return its stored path."""
        if not self.root:
            raise RuntimeError("no asset library configured")
        src = Path(src)
        d = KIND_DIRS.get(kind, [kind])[0]
        dest = self.root / d / (name or src.name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.write_bytes(src.read_bytes())
        return dest

    def list(self, kind: str | None = None) -> list[Path]:
        if not (self.root and self.root.exists()):
            return []
        if kind is None:
            return sorted(p for p in self.root.rglob("*") if p.is_file())
        out: list[Path] = []
        for d in KIND_DIRS.get(kind, [kind]):
            base = self.root / d
            if base.exists():
                out += sorted(p for p in base.rglob("*") if p.is_file())
        return out
