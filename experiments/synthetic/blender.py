"""Create calibrated synthetic drawings and independently render reconstructions.

Run with Blender --background --factory-startup --disable-autoexec.
Ground truth is written only under evaluator/. Reconstruction reads public PNGs.
"""
import argparse
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


def mesh_record(widths, depths, height, bevel):
    vertices = []
    for z, x, y in zip((-.5, .05, .5), widths, depths):
        for a, b in ((-1+bevel, -1), (1-bevel, -1), (1, -1+bevel), (1, 1-bevel),
                     (1-bevel, 1), (-1+bevel, 1), (-1, 1-bevel), (-1, -1+bevel)):
            vertices.append([a*x/2, b*y/2, z*height])
    faces = [list(reversed(range(8))), list(range(16, 24))]
    for ring in range(2):
        for n in range(8):
            m = (n+1) % 8
            faces.append([ring*8+n, ring*8+m, (ring+1)*8+m, (ring+1)*8+n])
    return {'vertices': vertices, 'faces': faces}


def setup():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = False
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 8
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.use_compositing = False
    scene.render.use_motion_blur = False
    scene.render.image_settings.file_format = 'PNG'
    camera_data = bpy.data.cameras.new('SyntheticCamera')
    camera = bpy.data.objects.new('SyntheticCamera', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 1.6
    mat = bpy.data.materials.new('SyntheticFlat')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (.16, .28, .48, 1)
    mat.node_tree.links.new(emission.outputs[0], output.inputs['Surface'])
    return scene, camera, mat


def render(scene, camera, mat, record, folder, views):
    me = bpy.data.meshes.new('SyntheticPart')
    me.from_pydata(record['vertices'], [], record['faces'])
    me.update()
    obj = bpy.data.objects.new('SyntheticPart', me)
    scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    for view, azimuth, elevation in views:
        a, e = math.radians(azimuth), math.radians(elevation)
        camera.location = Vector((4*math.sin(a)*math.cos(e), -4*math.cos(a)*math.cos(e), 4*math.sin(e)))
        camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (view+'.png')
        assert not path.exists()
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(me)


def main(root, stage):
    scene, camera, mat = setup()
    views = [('front', 0, 0), ('side', 90, 0), ('heldout', 37, 24)]
    if stage == 'source':
        assert not (root/'public.json').exists()
        rng = random.Random(20261015)
        truth = {}
        for index, case in enumerate(('S01', 'S02', 'S03')):
            width, depth, height = rng.uniform(.7, .9), rng.uniform(.65, .85), rng.uniform(.7, .9)
            truth[case] = {}
            for part in ('FL', 'FR', 'RL', 'RR'):
                depths = [depth*.88, depth, depth*.72]
                widths = [width*.84, width, width*.72]
                bevel = .22
                if index == 1 and part == 'RR':
                    depths = [d*1.22 for d in depths]
                if index == 2 and part == 'RR':
                    bevel = .55
                record = mesh_record(widths, depths, height, bevel)
                truth[case][part] = record
                render(scene, camera, mat, record, root/'reference'/case/part, views[:2])
                render(scene, camera, mat, record, root/'evaluator'/case/part, views[2:])
        write(root/'public.json', {'cases': list(truth), 'parts': ['FL', 'FR', 'RL', 'RR'],
                                  'resolution': 640, 'ortho_scale_m': 1.6,
                                  'section_height_fractions': [0, .55, 1], 'bevel_prior': .22,
                                  'protocol': 'Calibrated front/side drawings; section topology prior shared. Heldout images and truth are evaluator-only.',
                                  'predeclared_thresholds': {'normalized_vertex_rmse': .01, 'heldout_silhouette_iou': .97}})
        write(root/'evaluator/truth.json', truth)
        bpy.ops.wm.save_as_mainfile(filepath=str(root/'evaluator/source-generator-scene.blend'))
    else:
        candidate = json.loads((root/'candidates.json').read_text())
        for method, cases in candidate.items():
            for case, parts in cases.items():
                for part, record in parts.items():
                    render(scene, camera, mat, record, root/'rendered'/method/case/part, views)
    print('SYNTHETIC_STAGE_PASS', stage)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage', choices=['source', 'evaluate'])
    ap.add_argument('root', type=Path)
    args = ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    main(args.root.resolve(), args.stage)
