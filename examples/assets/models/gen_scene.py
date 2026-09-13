"""Generate a simple animated .blend: a spinning, bobbing torus over a plane.

Run:  blender -b -P gen_scene.py
This is a one-off helper to create the shared asset used by the examples.
"""
import bpy, math, os

# clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# camera
cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam)
cam_data.lens = 35
cam.location = (0, -13, 5.5)
cam.rotation_euler = (math.radians(67), 0, 0)
scene.camera = cam

# light
light_data = bpy.data.lights.new("Light", type='AREA')
light_data.energy = 800
light = bpy.data.objects.new("Light", light_data)
scene.collection.objects.link(light)
light.location = (4, -4, 6)

# torus
bpy.ops.mesh.primitive_torus_add(major_radius=2.0, minor_radius=0.6,
                                 major_segments=48, minor_segments=16)
torus = bpy.context.active_object
torus.name = "Torus"

# emissive-ish material
mat = bpy.data.materials.new("TorusMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.15, 0.7, 0.95, 1.0)
bsdf.inputs["Metallic"].default_value = 0.6
bsdf.inputs["Roughness"].default_value = 0.25
torus.data.materials.append(mat)

# plane
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -1.6))
plane = bpy.context.active_object
pmat = bpy.data.materials.new("PlaneMat")
pmat.use_nodes = True
pmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.03, 0.04, 0.06, 1)
plane.data.materials.append(pmat)

# animate torus spin + bob
scene.frame_start = 1
scene.frame_end = 72
torus.rotation_euler = (0, 0, 0)
torus.keyframe_insert("rotation_euler", frame=1)
torus.rotation_euler = (0, math.radians(360), 0)
torus.keyframe_insert("rotation_euler", frame=72)
torus.location = (0, 0, 0)
torus.keyframe_insert("location", frame=1)
torus.location = (0, 0, 0.4)
torus.keyframe_insert("location", frame=36)
torus.location = (0, 0, 0)
torus.keyframe_insert("location", frame=72)

# keep render cheap & deterministic
scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'SceneEEVEE') else scene.render.engine
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.fps = 30
scene.render.image_settings.file_format = 'PNG'

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "torus.blend")
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out)
