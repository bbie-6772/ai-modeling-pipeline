"""Bounded Blender adapter: approved local-space vertex edits on a new copy.

No generated Python, topology reconstruction, render, or automatic art judgment.
"""
import json
from pathlib import Path
import subprocess
from pipeline import local_file
from .executor import execute
from .specification import nonempty
from surface_gate import geometry


def validate_plan(plan, parts):
    if plan['kind'] != 'vertex-edits-v1' or set(plan['parts']) != set(parts):
        raise ValueError('Plan must cover exactly the approved operation parts')
    owners = {}
    for part, objects in plan['parts'].items():
        if not isinstance(objects, list) or not objects:
            raise ValueError('Explicit mesh object mapping required')
        for obj in objects:
            nonempty(obj)
            if obj in owners:
                raise ValueError('Mesh object belongs to multiple parts')
            owners[obj] = part
    edits = plan['edits']
    if not isinstance(edits, list) or not edits:
        raise ValueError('No vertex edits')
    seen = set()
    for edit in edits:
        if edit['object'] not in owners or type(edit['vertex']) is not int or edit['vertex'] < 0:
            raise ValueError('Edit outside plan scope or invalid vertex')
        key = edit['object'], edit['vertex']
        if key in seen:
            raise ValueError('Duplicate vertex edit')
        seen.add(key)
        # Reuse the established finite-coordinate validator.
        geometry({'vertices': [edit['position']], 'faces': [[0, 0, 0]]})


def execute_blender(run, root, output, blender, timeout=60):
    root = Path(root).resolve()
    path = run['operation']['plan']
    if not any(a['path'] == path and a['role'] == 'executor-plan' for a in run['assets']):
        raise ValueError('Approved registered executor plan required')
    plan_path = local_file(root, path)
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    validate_plan(plan, run['operation']['parts'])
    if Path(output).suffix.lower() != '.blend':
        raise ValueError('Blender output must be a .blend candidate')
    worker = Path(__file__).with_name('blender_worker.py').resolve()

    def adapter(candidate, parts):
        result = subprocess.run([str(blender), '--background', '--disable-autoexec',
                                 '--python-exit-code', '1', str(candidate), '--python', str(worker),
                                 '--', str(plan_path)], capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError('Blender edit failed: ' + result.stdout[-4000:] + result.stderr[-4000:])
    return execute(run, root, output, adapter)
