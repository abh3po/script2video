# Your asset library

This folder is where *your* reusable assets live (`.blend` models, textures,
music beds, reference voice clips, SVGs). It is deliberately **not** committed:
the code is shared, your content is not.

Scripts can reference any file here by bare name:

```markdown
<!-- visual: blender | atom -->      -> assets/models/atom.blend
<!-- visual: image   | diagram.png --> -> assets/images/diagram.png
<!-- visual: svg     | atom.svg -->    -> assets/svg/atom.svg
```

Expected subfolders (created on demand):

```
assets/
  models/     .blend, .glb/.gltf, .fbx, Godot projects
  textures/   images used by materials
  images/     generic stills
  svg/        vector art
  audio/      music beds, cloned-voice reference clips
  fonts/
```

Point `assets_dir` in your config at any folder you like. The bundled
`examples/assets/` demonstrates the format with a Blender torus and a small
Godot project.

The expensive renders are cached separately in `cache_dir` (default
`~/.cache/s2v`), keyed by source content, so a model used in many scenes or
many videos is only rendered once.
