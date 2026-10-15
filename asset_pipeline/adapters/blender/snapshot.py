"""Read-only evaluated world geometry export from a saved Blender file.

blender --background --disable-autoexec candidate.blend --python
asset_pipeline/adapters/blender/snapshot.py -- --parts parts.json --output after.json
parts.json: {"body": ["Body"], "left_arm": ["UpperArm.L", "Forearm.L"]}
Output is exclusive-create. The scene and source blend are never saved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--asset-path', required=True, help='Source path relative to gate config')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source = Path(bpy.data.filepath)
    if not bpy.data.filepath or bpy.data.is_dirty:
        raise ValueError('Open an unchanged saved source in a fresh Blender process')
    with source.open('rb') as stream:
        before_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    mapping = json.loads(args.parts.read_text(encoding='utf-8'))
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError('Expected nonempty part to object-list mapping')
    depsgraph = bpy.context.evaluated_depsgraph_get()
    parts, seen = {}, set()
    for part, names in mapping.items():
        if not isinstance(names, list) or not names:
            raise ValueError('Part needs explicit mesh object names')
        vertices, faces = [], []
        triangle_count = 0
        for name in names:
            if name in seen:
                raise ValueError('Object appears in multiple parts: ' + name)
            seen.add(name)
            obj = bpy.data.objects[name]
            if obj.type != 'MESH':
                raise ValueError('Only mesh objects supported: ' + name)
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            try:
                offset = len(vertices)
                vertices.extend([list(evaluated.matrix_world @ v.co) for v in mesh.vertices])
                faces.extend([[offset + i for i in f.vertices] for f in mesh.polygons])
                mesh.calc_loop_triangles()
                triangle_count += len(mesh.loop_triangles)
            finally:
                evaluated.to_mesh_clear()
        if not vertices:
            raise ValueError('Part has no evaluated vertices: ' + part)
        lower = [min(v[axis] for v in vertices) for axis in range(3)]
        upper = [max(v[axis] for v in vertices) for axis in range(3)]
        parts[part] = dict(objects=names, vertices=vertices, faces=faces,
                           measurements=dict(vertex_count=len(vertices), face_count=len(faces),
                               triangle_count=triangle_count, bounds_min=lower, bounds_max=upper,
                               dimensions=[upper[i] - lower[i] for i in range(3)]))
    with source.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != before_hash:
            raise ValueError('Source changed during export')
    payload = dict(source_asset=args.asset_path, source_sha256=before_hash,
                   coordinate_space='world', blender_version=bpy.app.version_string, parts=parts,
                   scene_units=dict(system=bpy.context.scene.unit_settings.system,
                                    scale_length=bpy.context.scene.unit_settings.scale_length))
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(payload, stream, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
