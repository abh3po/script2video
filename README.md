# script2video (`s2v`)

Turn a written script into a narrated video. Scenes are parsed from a
Markdown/plain-text file, narrated with **Qwen3-TTS** (or edge-tts / piper /
espeak for drafts), illustrated with text slides, images, SVG, **Blender**
renders or **Godot** captures, then stitched with ffmpeg into a finished video
with optional soft or burned-in subtitles.

## Install

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .            # core (parsing, slides, ffmpeg composition)
pip install -e '.[qwen]'    # + Qwen3-TTS (needs a CUDA GPU + torch)
pip install -e '.[edge]'    # + edge-tts, the easy network fallback
```

External tools are only needed for the visual kinds you use:

| visual kind | needs                    |
| ----------- | ------------------------ |
| `slide`     | nothing (built in)       |
| `image`     | nothing (built in)       |
| `svg`       | `rsvg-convert` / `inkscape` / `cairosvg` |
| `video`     | `ffmpeg`                 |
| `blender`   | `blender`                |
| `godot`     | `godot`                  |

`ffmpeg`/`ffprobe` are always required. Run `s2v check` to see what is present.

## Quick start

```bash
s2v check                                   # what's available
s2v parse examples/fermi.md                 # see how scenes were split
s2v build examples/fermi.md -o build/fermi  # render the video
```

Draft render with the always-available network voice:

```bash
s2v build examples/fermi.md -o build/fermi --engine edge --voice en-US-GuyNeural
```

Final render with Qwen3-TTS:

```bash
s2v build examples/fermi.md -o build/fermi -c config.example.yaml
```

The repo ships a small, self-contained demo (a Blender torus and a Godot
project under `examples/assets/`) so you can render real 3D without owning any
assets yet:

```bash
s2v build examples/3d_demo.md -o build/demo -c examples/config.yaml
```

Output layout:

```
build/fermi/
  output.mp4          # final video (video + narration + soft subtitles)
  subtitles.srt
  stitched.mp4        # before music/subtitle muxing
  scenes/000/
    narration.wav     # per-scene voiceover
    slide.png         # rendered visual
    clip.mp4          # scene video with audio
```

## Script format

Scenes start at a `##`–`######` heading or a line of `---`. A top-level `#`
heading is treated as the document title. Body text is narration; a slide's
label (the part after `|`) is shown on screen but is **not** read aloud, so
title cards and timed slides stay silent. Optional directives:

```markdown
## The Silent Sky

Look up on a clear night and you will see a few thousand stars.

<!-- visual: slide | The Silent Sky -->
<!-- instruct: speak slowly and thoughtfully -->

## The Atom

<!-- visual: blender | atom -->        <!-- resolved from assets/models/atom.blend -->
<!-- duration: 6.5 -->                 <!-- used when there is no narration -->

## A Diagram

<!-- visual: image | diagram.png -->
<!-- visual: svg   | atom.svg -->
<!-- visual: video | intro.mp4 -->
<!-- visual: godot | projects/my_game -->
```

Per-scene `speaker`, `language`, `instruct` and `voice` directives override the
run config for that scene.

## Reusing assets across videos

Everything expensive lives outside the build output so it can be reused:

* **Asset library** (`assets_dir`, default `./assets`) — one place for `.blend`
  models, textures, music and reference audio. Scripts refer to assets by bare
  name (`<!-- visual: blender | atom -->`) and s2v searches
  `models/`, `textures/`, `svg/`, `images/`, `audio/`. No per-video copying.
* **Render cache** (`cache_dir`, default `~/.cache/s2v`) — content-addressed by
  the inputs that change the pixels. A Blender or Godot render, or a TTS clip,
  is produced **once** and reused in every scene and every later video that
  needs the identical result. Cache hits are reported as `(cached)`.

```bash
s2v assets                      # list the library and cache size
s2v assets --add blender=~/Downloads/robot.blend --name robot
s2v assets --clear-cache
s2v build script.md --no-cache  # bypass the cache for one run
```

Because the cache key includes the source file hash, editing a `.blend` or the
narration text automatically invalidates just that entry.

## TTS engines

| engine  | install            | notes                                              |
| ------- | ------------------ | -------------------------------------------------- |
| `qwen`  | `pip install qwen-tts` | GPU, best quality. CustomVoice, VoiceDesign, voice clone |
| `edge`  | `pip install edge-tts` | free Microsoft neural voices, needs internet     |
| `piper` | `pip install piper-tts`| fully offline, fast                              |
| `espeak`| system package     | always available, robotic, good for drafts         |

Qwen3-TTS models:

* `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` — fixed speakers (`Ryan`, `Aiden`,
  `Vivian`, `Serena`, `Uncle_Fu`, …), optional `instruct` style prompt.
* `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` — describe the voice in `instruct`.
* `Qwen/Qwen3-TTS-12Hz-1.7B-Base` — 3-second voice cloning via
  `tts.ref_audio` + `tts.ref_text`.

```bash
s2v voices --model Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice
```

Qwen3-TTS expects a modern Python (3.10+); on some distros the system Python is
missing extension modules (`_bz2`, `_lzma`). Use a full interpreter (e.g.
`python3.12 -m venv`).

## Blender and Godot

The Blender renderer runs `blender -b <file> -a`, overrides the frame range to
match the scene duration and encodes the PNG sequence.

The Godot renderer records the project with Movie Maker mode. Godot's
`--headless` flag uses a **dummy** renderer that produces no pixels, so s2v
runs Godot against an X display: on a desktop it uses `$DISPLAY`, otherwise it
wraps the call in `xvfb-run` (the virtual screen is made slightly larger than
the requested resolution so the viewport is not clipped). Vulkan on the GPU is
the default rendering driver and yields exact-size frames.

```yaml
visuals:
  godot_display: auto      # auto | xvfb | none
  godot_renderer: vulkan   # or opengl3 on machines without Vulkan
```

Both results are content-addressed in the cache, so a 3D model or animation
used across many scenes — and across many videos — is rendered only once.

## Configuration

See `config.example.yaml`. CLI flags override the config file; both override
defaults. Notable keys: `width`, `height`, `fps`, `pad` (silence after each
line), `crossfade`, `subtitles`, `subtitle_burn`, `music`, `assets_dir`,
`cache_dir`, and the `tts` / `visuals` blocks.

## Commands

```
s2v build SCRIPT [-o DIR] [-c CONFIG] [--engine E] [--assets DIR] [--no-cache]
s2v parse SCRIPT         # JSON dump of parsed scenes (debug your script)
s2v voices               # list Qwen speakers/languages
s2v check                # verify ffmpeg and optional tools
s2v assets [--add KIND=PATH] [--clear-cache]
```

## Tests

The smoke tests need only ffmpeg (no TTS, Blender or Godot):

```bash
python tests/test_pipeline.py     # or: pytest -q
```

CI runs them on every push and pull request.

## License

MIT. The `assets/` folder is gitignored — the code is shared, your media is not.
