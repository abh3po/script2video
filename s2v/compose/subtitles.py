"""Subtitle generation.

Word-level timing comes from the Qwen ``ForcedAligner`` when available;
otherwise text is distributed proportionally across the scene duration. Output
is a standard SRT file (also usable for burned-in captions and for driving
Blender/Godot animations later).
"""

from __future__ import annotations

import re
from pathlib import Path

from ..model import Scene


def format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _chunks(text: str, max_len: int = 88) -> list[str]:
    sentences = re.split(r"(?<=[.!?…])\s+", text.strip())
    chunks: list[str] = []
    for sentence in sentences:
        if not sentence:
            continue
        if len(sentence) <= max_len:
            chunks.append(sentence)
            continue
        current = ""
        for word in sentence.split():
            if current and len(current) + 1 + len(word) > max_len:
                chunks.append(current)
                current = word
            else:
                current = f"{current} {word}".strip()
        if current:
            chunks.append(current)
    return chunks or ([text] if text else [])


def build_scene_entries(scene: Scene, start: float) -> list[tuple[float, float, str]]:
    """Return ``(start, end, text)`` subtitle entries for one scene."""
    text = scene.spoken_text()
    if not text:
        return []
    chunks = _chunks(text)
    end_of_scene = start + scene.duration

    if scene.word_timings:
        return _entries_from_word_timings(scene, start)

    # proportional distribution by character count
    total_chars = sum(len(c) for c in chunks) or 1
    entries: list[tuple[float, float, str]] = []
    cursor = start
    for chunk in chunks:
        span = (len(chunk) / total_chars) * (end_of_scene - start)
        entries.append((cursor, min(cursor + span, end_of_scene), chunk))
        cursor += span
    return entries


def _entries_from_word_timings(scene: Scene, start: float) -> list[tuple[float, float, str]]:
    entries: list[tuple[float, float, str]] = []
    words = scene.word_timings
    group: list[dict] = []
    for word in words:
        group.append(word)
        if len(group) >= 8 or word["text"].endswith((".", "!", "?", "…")):
            first, last = group[0], group[-1]
            text = " ".join(w["text"] for w in group)
            entries.append((start + first["start"], start + last["end"], text))
            group = []
    if group:
        first, last = group[0], group[-1]
        entries.append((start + first["start"], start + last["end"], " ".join(w["text"] for w in group)))
    return entries


def format_srt(entries: list[tuple[float, float, str]]) -> str:
    blocks = []
    for i, (start, end, text) in enumerate(entries, 1):
        blocks.append(
            f"{i}\n{format_timestamp(start)} --> {format_timestamp(end)}\n{text}\n"
        )
    return "\n".join(blocks)


def assemble_srt(scenes: list[Scene]) -> str:
    entries: list[tuple[float, float, str]] = []
    cursor = 0.0
    for scene in scenes:
        entries.extend(build_scene_entries(scene, cursor))
        cursor += scene.duration
    return format_srt(entries)


def write_srt(scenes: list[Scene], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(assemble_srt(scenes), encoding="utf-8")
    return path
