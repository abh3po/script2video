"""Parse a Markdown/plain-text script into scenes.

Supported scene separators (pick whichever fits the script):

  * a Markdown heading ``## Scene title`` starts a new scene
  * a line of only dashes ``---`` starts a new scene
  * a blank line followed by another paragraph *does not* split (paragraphs
    inside a scene are joined)

Per-scene directives (HTML comments, optional):

    <!-- visual: image | assets/diagram.png -->
    <!-- visual: blender | scenes/atom.blend -->
    <!-- visual: godot | projects/my_game -->
    <!-- duration: 6.5 -->          (only used when there is no narration)
    <!-- speaker: Aiden -->
    <!-- instruct: speak slowly and warmly -->

Text in a scene is narration. Markdown emphasis is stripped for speech.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from .model import BLENDER, GODOT, IMAGE, SLIDE, SVG, VIDEO, Scene, Visual

#: level 2-6 headings split scenes; a top-level "#" is the document title
_HEADING_RE = re.compile(r"^\s{0,3}#{2,6}\s+(.*?)\s*#*\s*$")
_TITLE_RE = re.compile(r"^\s{0,3}#\s+(.*?)\s*#*\s*$")
_DIRECTIVE_RE = re.compile(r"<!--\s*([a-zA-Z_]+)\s*:\s*(.*?)\s*-->")
_INLINE_MD = [
    (re.compile(r"!\[(.*?)\]\(.*?\)"), r"\1"),
    (re.compile(r"\[(.*?)\]\(.*?\)"), r"\1"),
    (re.compile(r"\*\*(.*?)\*\*"), r"\1"),
    (re.compile(r"__(.*?)__"), r"\1"),
    (re.compile(r"\*(.*?)\*"), r"\1"),
    (re.compile(r"_(.*?)_"), r"\1"),
    (re.compile(r"`(.*?)`"), r"\1"),
]

_KNOWN_KINDS = {SLIDE, IMAGE, SVG, BLENDER, GODOT, VIDEO}


def strip_markdown(text: str) -> str:
    for pattern, repl in _INLINE_MD:
        text = pattern.sub(repl, text)
    return text


def _split_front_matter(text: str) -> tuple[dict, str]:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            import yaml

            header = yaml.safe_load(text[4:end]) or {}
            return header, text[end + 4 :]
    return {}, text


def parse_script(path: str | Path) -> tuple[dict, list[Scene]]:
    """Parse *path* and return ``(front_matter, scenes)``."""
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    meta, body = _split_front_matter(raw)

    scenes: list[Scene] = []
    current_title: str | None = None
    current_lines: list[str] = []
    current_pending_visual: Visual | None = None
    current_params: dict = {}

    def flush() -> None:
        nonlocal current_title, current_lines, current_pending_visual, current_params
        if not current_lines and current_pending_visual is None and current_title is None:
            return
        narration = strip_markdown(" ".join(current_lines).strip())
        visual = current_pending_visual or Visual(kind="slide")
        if visual.kind == SLIDE and not visual.source:
            visual.source = current_title or narration
        scene = Scene(index=len(scenes), title=current_title, narration=narration, visual=visual)
        scene.visual.params.update(current_params)
        scenes.append(scene)
        current_title, current_lines, current_pending_visual, current_params = None, [], None, {}

    for line in body.splitlines():
        title_match = _TITLE_RE.match(line)
        if title_match:
            # a leading H1 is the document title, not a scene
            meta.setdefault("title", strip_markdown(title_match.group(1)).strip())
            flush()
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            flush()
            current_title = strip_markdown(heading.group(1)).strip()
            continue

        stripped = line.strip()
        if stripped == "---":
            flush()
            continue

        directive = _DIRECTIVE_RE.search(line)
        if directive:
            key, value = directive.group(1), directive.group(2)
            if key.lower() == "visual":
                parts = value.split("|", 1)
                kind = parts[0].strip().lower()
                source = parts[1].strip() if len(parts) > 1 else None
                if kind in _KNOWN_KINDS:
                    current_pending_visual = Visual(kind=kind, source=source)
                else:
                    current_pending_visual = Visual(kind=IMAGE, source=value.strip())
            elif key.lower() == "duration":
                try:
                    current_params["duration"] = float(value)
                except ValueError:
                    pass
            else:
                current_params[key.lower()] = value
            continue

        if not stripped:
            continue

        current_lines.append(stripped)

    flush()
    return meta, scenes


def iter_scene_dirs(out_dir: Path, scenes: list[Scene]) -> Iterator[Path]:
    for scene in scenes:
        yield out_dir / "scenes" / f"{scene.index:03d}"
