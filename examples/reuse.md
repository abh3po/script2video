---
title: Reusing 3D assets across videos
---

## The shared model

This scene renders a Blender model from the shared asset library. Because the
render is cached by file content, every later video that uses the same model
and camera move reuses this render instantly.

<!-- visual: blender | torus -->
<!-- duration: 6 -->

## The same model again

The next scene asks for the identical model. The cache means no second render.

<!-- visual: blender | torus -->
<!-- duration: 4 -->
