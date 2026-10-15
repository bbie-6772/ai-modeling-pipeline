"""Real Blender smoke test, temporary cubes only; no production asset touched."""
import json
import os
from pathlib import Path
import subprocess
import unittest

from pipeline import digest
from asset_pipeline.blender_adapter import execute_blender
from asset_pipeline.specification import STAGES
from test_asset_pipeline import CoreTest as _Fixture


def load_tests(loader, tests, pattern):
    # The imported fixture class must not duplicate its unit tests in discovery.
    return loader.loadTestsFromTestCase(BlenderExecutorTest)


@unittest.skipUnless(os.environ.get('BLENDER_BIN'), 'Set BLENDER_BIN for real Blender executor integration')
class BlenderExecutorTest(unittest.TestCase):
    def test_real_edit_reopen_snapshot_and_protected_object(self):
        fixture = _Fixture()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        root = fixture.root
        blender = os.environ['BLENDER_BIN']
        def run(args):
            result = subprocess.run([blender, '--background', '--disable-autoexec', '--python-exit-code', '1', *args],
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        script = root/'create.py'
        script.write_text('''import bpy
from pathlib import Path
root = Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
bpy.context.object.name = 'Body'
bpy.ops.mesh.primitive_cube_add(location=(5,0,0))
bpy.context.object.name = 'Protected'
bpy.ops.wm.save_as_mainfile(filepath=str(root/'baseline.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(root/'candidate.blend'))
''', encoding='utf-8')
        run(['--factory-startup', '--python', str(script)])
        for role in ('baseline', 'candidate'):
            path = role + '.blend'
            fixture.run['assets'].append(dict(path=path, role=role, sha256=digest(root/path)))
            fixture.run[role] = path
        fixture.run['revisions'] = []
        fixture.run['qa'] = {k: dict(status='UNKNOWN', observation='Not run') for k in fixture.run['qa']}
        plan = dict(kind='vertex-edits-v1', parts={'body': ['Body']},
                    edits=[dict(object='Body', vertex=0, position=[-1, -1, -.75])])
        fixture.add_asset('plan.json', 'executor-plan', plan)
        fixture.run['operation']['plan'] = 'plan.json'
        fixture.stage(STAGES[2])
        frozen = {a['path']: digest(root/a['path']) for a in fixture.run['assets']}
        receipt = execute_blender(fixture.run, root, 'edited.blend', blender)
        self.assertEqual(receipt['status'], 'candidate-pending-qa', receipt)
        self.assertNotEqual(receipt['before_sha256'], receipt['after_sha256'])
        self.assertEqual(frozen, {p: digest(root/p) for p in frozen})
        exporter = Path(__file__).with_name('blender_surface_snapshot.py').resolve()
        (root/'parts.json').write_text(json.dumps({'body': ['Body'], 'protected': ['Protected']}))
        for name in ('candidate', 'edited'):
            run([str(root/(name+'.blend')), '--python', str(exporter), '--',
                 '--parts', str(root/'parts.json'), '--output', str(root/(name+'.json')),
                 '--asset-path', name+'.blend'])
        before = json.loads((root/'candidate.json').read_text())['parts']
        after = json.loads((root/'edited.json').read_text())['parts']
        self.assertNotEqual(before['body'], after['body'])
        self.assertEqual(before['protected'], after['protected'])
        self.assertEqual(after['body']['vertices'][0], [-1, -1, -.75])
