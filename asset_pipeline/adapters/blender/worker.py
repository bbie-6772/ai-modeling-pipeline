"""Blender subprocess only. Validate all edits before touching candidate geometry."""
import json
from pathlib import Path
import sys


def main():
    import bpy
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from asset_pipeline.adapters.blender.adapter import validate_plan
    plan = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text(encoding='utf-8'))
    validate_plan(plan, plan['parts'])
    names = {n for objects in plan['parts'].values() for n in objects}
    objects = {n: bpy.data.objects[n] for n in names}
    for name, obj in objects.items():
        if obj.type != 'MESH' or obj.library or obj.data.library or obj.data.shape_keys:
            raise ValueError('Only local mesh objects without shape keys supported: ' + name)
        # Reject shared mesh edits rather than accidentally modifying another part.
        if obj.data.users != 1:
            raise ValueError('Shared mesh data requires explicit reconstruction: ' + name)
    for edit in plan['edits']:
        if edit['vertex'] >= len(objects[edit['object']].data.vertices):
            raise ValueError('Vertex index out of bounds')
    for edit in plan['edits']:
        objects[edit['object']].data.vertices[edit['vertex']].co = edit['position']
    for obj in objects.values():
        obj.data.update()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)


if __name__ == '__main__':
    main()
