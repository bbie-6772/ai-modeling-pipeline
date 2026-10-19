"""Blender subprocess: render one evaluated snapshot with three fixed ORTHO cameras."""
import json
from pathlib import Path
import sys


def main():
    import bpy
    from mathutils import Vector
    if not bpy.app.background:
        raise ValueError('Drawing renderer requires an isolated background process')
    root = Path(sys.argv[sys.argv.index('--')+1])
    snapshot = json.loads((root/'snapshot.json').read_text(encoding='utf-8'))
    config = json.loads((root/'render-config.json').read_text(encoding='utf-8'))
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from asset_pipeline.drawing import COLORS
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = scene.render.resolution_y = config['resolution']
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    shading = scene.display.shading
    shading.light = 'STUDIO'
    shading.studio_light = 'paint.sl'
    shading.color_type = 'OBJECT'
    shading.show_shadows = False
    shading.show_cavity = False
    shading.show_specular_highlight = False
    shading.show_object_outline = True
    shading.object_outline_color = (0.08, 0.12, 0.16)
    scene.display.render_aa = '8'
    scale = snapshot['scene_units']['scale_length']
    for i, (name, record) in enumerate(sorted(snapshot['parts'].items())):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([[c*scale for c in v] for v in record['vertices']], [], record['faces'])
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        scene.collection.objects.link(obj)
        color = COLORS[i % len(COLORS)].lstrip('#')
        obj.color = tuple(int(color[j:j+2],16)/255 for j in (0,2,4))+(1,)
    camera = bpy.data.objects.new('DrawingCamera', bpy.data.cameras.new('DrawingCamera'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.clip_start = config['distance_m']/10000
    camera.data.clip_end = config['distance_m']*4
    for name, view in config['views'].items():
        camera.location = view['camera_location']
        camera.rotation_euler = (Vector(view['camera_target'])-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.ortho_scale = view['ortho_scale_m']
        scene.render.filepath = str(root/(name+'.png'))
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
