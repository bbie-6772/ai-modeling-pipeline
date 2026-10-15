"""Blender CLI replay pilot: independent paw shells vs one shared mirror recipe.

This measures execution/review packaging, not fresh AI modeling or human review.
Run inside Blender with --disable-autoexec; see --help arguments after --.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def dump(path, data):
    # Never overwrite an experiment result.
    with path.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def key(leg):
    return f'N15_Paw_{leg}_Shell'


def mesh_record(obj):
    return {'vertices': [list(obj.matrix_world @ v.co) for v in obj.data.vertices],
            'faces': [list(p.vertices) for p in obj.data.polygons],
            'materials': [obj.material_slots[p.material_index].material.name for p in obj.data.polygons],
            'smooth': [p.use_smooth for p in obj.data.polygons]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage', choices=['extract', 'A', 'B', 'check'])
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--recipe', type=Path, required=True)
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:])
    scene = bpy.data.scenes['Minor_On_Air_New_Parts_20261015']
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    guard = load('experiment_guard', args.project / 'pipeline/body_guard.py')
    legs = ['FL', 'FR', 'RL', 'RR']
    allowed = {key(l) for l in legs}
    if args.stage == 'extract':
        assert 'preview_v11' in Path(bpy.data.filepath).name
        planes = [scene.objects[f'N15_Leg_{l}_Pivot'].matrix_world.translation.y for l in legs]
        yc = (planes[0] + planes[2]) / 2
        assert abs(yc - (planes[1] + planes[3]) / 2) < 1e-6
        dump(args.recipe, {'source': bpy.data.filepath, 'source_sha256': sha(Path(bpy.data.filepath)),
                          'symmetry_y': yc, 'shells': {l: mesh_record(scene.objects[key(l)]) for l in legs},
                          'provenance': 'Unadopted v11 preview replay; no new source-point interpretation.'})
        return
    recipe = json.loads(args.recipe.read_text(encoding='utf-8'))
    if args.stage == 'check':
        baseline = json.loads((args.out / 'guard_before.json').read_text())
        current = {o.name: guard._digest_object(o) for o in scene.objects if o.name not in allowed}
        assert current == baseline['objects'], 'Protected objects changed on reopen'
        assert {m.name: guard._digest_material(m) for m in bpy.data.materials} == baseline['materials']
        assert sorted(o.name for o in scene.objects) == baseline['names']
        stats = {}
        import bmesh
        for leg in legs:
            obj = scene.objects[key(leg)]
            assert obj.data.users == 1
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            me = evaluated.to_mesh()
            bm = bmesh.new()
            try:
                bm.from_mesh(me)
                stats[leg] = {'boundary_edges': sum(e.is_boundary for e in bm.edges),
                              'zero_area_faces': sum(f.calc_area() < 1e-10 for f in bm.faces),
                              'winding_conflicts': sum(e.is_manifold and not e.is_contiguous for e in bm.edges)}
                assert all(v == 0 for v in stats[leg].values()), stats
            finally:
                bm.free()
                evaluated.to_mesh_clear()
        dump(args.out / 'reopen_check.json', {'passed': True, 'mesh_checks': stats,
                                            'protected_objects': len(current)})
        return
    assert Path(bpy.data.filepath).name == 'model_ear_v02_cpu.blend'
    args.out.mkdir(exist_ok=False)
    protected = {o.name: guard._digest_object(o) for o in scene.objects if o.name not in allowed}
    materials = {m.name: guard._digest_material(m) for m in bpy.data.materials}
    names = sorted(o.name for o in scene.objects)
    dump(args.out / 'guard_before.json', {'objects': protected, 'materials': materials, 'names': names})
    object_metadata = {l: (scene.objects[key(l)].matrix_world.copy(),
                          [m.name for m in scene.objects[key(l)].data.materials],
                          [(m.name, m.type) for m in scene.objects[key(l)].modifiers]) for l in legs}
    started = time.perf_counter()
    for leg in legs:
        obj = scene.objects[key(leg)]
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        if args.stage == 'A':
            record = recipe['shells'][leg]
            verts = [Vector(v) for v in record['vertices']]
            faces = record['faces']
        else:
            record = recipe['shells']['FL']
            mx, my = leg in ('FR', 'RR'), leg in ('RL', 'RR')
            verts = [Vector((-v[0] if mx else v[0], 2*recipe['symmetry_y']-v[1] if my else v[1], v[2]))
                     for v in record['vertices']]
            faces = [list(reversed(f)) if mx != my else f for f in record['faces']]
        inv = obj.matrix_world.inverted()
        obj.data.clear_geometry()
        obj.data.from_pydata([tuple(inv @ v) for v in verts], [], faces)
        slots = [m.name for m in obj.data.materials]
        for polygon, mat, smooth in zip(obj.data.polygons, record['materials'], record['smooth']):
            polygon.material_index = slots.index(mat)
            polygon.use_smooth = smooth
        obj.data.update()
    bpy.context.view_layer.update()
    build_seconds = time.perf_counter() - started
    def verify():
        assert protected == {o.name: guard._digest_object(o) for o in scene.objects if o.name not in allowed}
        assert materials == {m.name: guard._digest_material(m) for m in bpy.data.materials}
        assert names == sorted(o.name for o in scene.objects)
        for leg in legs:
            obj = scene.objects[key(leg)]
            matrix, slots, modifiers = object_metadata[leg]
            assert obj.matrix_world == matrix
            assert [m.name for m in obj.data.materials] == slots
            assert [(m.name, m.type) for m in obj.modifiers] == modifiers
    verify()
    candidate = args.out / 'candidate.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(candidate), copy=True)
    dump(args.out / 'geometry.json', {l: mesh_record(scene.objects[key(l)]) for l in legs})
    # Render changes are temporary and never saved into candidate.blend.
    camera = scene.objects['N15_Camera_Front']
    scene.camera = camera
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 2
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 8
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.use_compositing = False
    scene.render.use_motion_blur = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = True
    for collection in bpy.data.collections:
        if 'Expression' in collection.name:
            collection.hide_render = True
    metrics = {'method': args.stage, 'build_seconds': build_seconds, 'renders': [],
               'human_review_seconds': None, 'tokens': None, 'revisions': None,
               'quality_approved': False, 'candidate_adopted': False,
               'baseline_sha256': sha(Path(bpy.data.filepath)), 'recipe_sha256': sha(args.recipe),
               'blender_version': bpy.app.version_string,
               'limitations': 'Deterministic replay, not independent AI modeling; no calibrated source conformance score.'}
    views8 = [('front', 0, 0), ('rear', 180, 0), ('left', 90, 0), ('right', 270, 0),
              ('top', 0, 89.9), ('bottom', 0, -89.9), ('oblique1', 35, 20), ('oblique2', 215, 20)]
    groups = [(l, {key(l)}, views8) for l in legs] if args.stage == 'A' else [
        ('group', allowed, [('front', 0, 0), ('oblique', 35, 20), ('bottom', 0, -89.9)])]
    for label, visible, views in groups:
        pts = [scene.objects[n].matrix_world @ v.co for n in visible for v in scene.objects[n].data.vertices]
        target = Vector([(min(v[i] for v in pts)+max(v[i] for v in pts))/2 for i in range(3)])
        scale = max(max(v[i] for v in pts)-min(v[i] for v in pts) for i in range(3)) * 1.7
        for obj in scene.objects:
            if obj.type in ('MESH', 'CURVE'):
                obj.hide_render = obj.name not in visible
        for name, angle, elev in views:
            a, e = math.radians(angle), math.radians(elev)
            camera.data.type = 'ORTHO'
            camera.data.ortho_scale = scale
            camera.location = target + Vector((5*math.sin(a)*math.cos(e), -5*math.cos(a)*math.cos(e), 5*math.sin(e)))
            camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str(args.out / f'{label}_{name}.png')
            t = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            metrics['renders'].append({'file': str(scene.render.filepath), 'seconds': time.perf_counter()-t,
                                      'target': list(target), 'angle': angle, 'elevation': elev, 'ortho_scale': scale})
            print('PILOT_PROGRESS', args.stage, label, name, flush=True)
    metrics['render_seconds'] = sum(r['seconds'] for r in metrics['renders'])
    metrics['render_count'] = len(metrics['renders'])
    dump(args.out / 'metrics.json', metrics)


if __name__ == '__main__':
    main()
