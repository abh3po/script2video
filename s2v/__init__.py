"""s2v - script to video pipeline (narration + slides / Blender / Godot / SVG).

Turn a script (Markdown/plain text with scene headers) into a video by:
  1. parsing scenes from the script,
  2. synthesizing narration per scene (Qwen3-TTS and friends),
  3. rendering a visual per scene (text slide, image, SVG, Blender, Godot clip),
  4. composing everything with ffmpeg (subtitles optional).
"""

__version__ = "0.1.0"
