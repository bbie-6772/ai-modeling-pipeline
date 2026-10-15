"""Opt-in integration test. Uses a new temporary synthetic scene only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from surface_gate import geometry_delta


@unittest.skipUnless(os.environ.get('BLENDER_BIN'), 'Set BLENDER_BIN for real Blender integration')
class BlenderSurfaceTest(unittest.TestCase):
    def test_export_saved_evaluated_geometry_and_preserve_sources(self):
        blender = os.environ['BLENDER_BIN']
        exporter = Path(__file__).with_name('blender_surface_snapshot.py').resolve()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            script = root/'create.py'
            script.write_text('''import bpy
from pathlib import Path
root = Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
obj.name = 'Body'
obj.location.x = 2
obj.modifiers.new('EvaluatedTriangulation', 'TRIANGULATE')
bpy.ops.wm.save_as_mainfile(filepath=str(root/'before.blend'))
obj.data.vertices[0].co.z -= .25
bpy.ops.wm.save_as_mainfile(filepath=str(root/'after.blend'))
''', encoding='utf-8')
            def run(args):
                return subprocess.run([blender, '--background', '--disable-autoexec', '--python-exit-code', '1', *args],
                                      capture_output=True, text=True, timeout=60)
            result = run(['--factory-startup', '--python', str(script)])
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            (root/'parts.json').write_text('{"body": ["Body"]}')
            hashes = {}
            for phase in ('before', 'after'):
                source = root/(phase+'.blend')
                hashes[phase] = hashlib.sha256(source.read_bytes()).hexdigest()
                args = [str(source), '--python', str(exporter), '--', '--parts', str(root/'parts.json'),
                        '--output', str(root/(phase+'.json')), '--asset-path', phase+'.blend']
                result = run(args)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), hashes[phase])
                # Exclusive-create must fail rather than overwrite prior evidence.
                self.assertNotEqual(run(args).returncode, 0)
            before, after = [json.loads((root/(p+'.json')).read_text()) for p in ('before', 'after')]
            delta = geometry_delta(before['parts']['body'], after['parts']['body'])
            self.assertTrue(delta['existing_surface_changed'])
            self.assertEqual(delta['removed_or_moved_vertices'], 1)
            self.assertEqual(before['source_sha256'], hashes['before'])
            self.assertGreaterEqual(min(v[0] for v in before['parts']['body']['vertices']), 1)
            self.assertEqual(len(before['parts']['body']['faces']), 12)


if __name__ == '__main__':
    unittest.main()
