"""Actual fixed-camera drawings from a temporary, deliberately asymmetric model."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib

from asset_pipeline.drawing import generate
from asset_pipeline.files import digest
from asset_pipeline.shape_contract import evaluate,verify_drawings


def alpha_bounds(path, landmarks=()):
    """Read Blender's 8-bit RGBA PNG using only the standard library."""
    data = path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Not a PNG')
    offset, compressed = 8, bytearray()
    while offset < len(data):
        size = struct.unpack('>I', data[offset:offset+4])[0]
        kind, payload = data[offset+4:offset+8], data[offset+8:offset+8+size]
        if kind == b'IHDR':
            width,height,depth,color,_,_,interlace = struct.unpack('>IIBBBBB', payload)
            if (depth,color,interlace) != (8,6,0):
                raise ValueError('Expected noninterlaced 8-bit RGBA')
        if kind == b'IDAT':
            compressed.extend(payload)
        offset += size+12
    raw, stride, previous, points = zlib.decompress(compressed), width*4, bytearray(width*4), []
    for y in range(height):
        start = y*(stride+1)
        filtering, row = raw[start], bytearray(raw[start+1:start+1+stride])
        for i in range(stride):
            a,b,c = row[i-4] if i>=4 else 0, previous[i], previous[i-4] if i>=4 else 0
            p = a+b-c
            pa,pb,pc = abs(p-a),abs(p-b),abs(p-c)
            predictor = a if pa<=pb and pa<=pc else b if pb<=pc else c
            adjustment = (0,a,b,(a+b)//2,predictor)[filtering]
            row[i] = (row[i]+adjustment)&255
        points.extend((x,y) for x in range(width) if row[x*4+3]>=128)
        previous = row
    if not set(landmarks) <= set(points):
        raise ValueError('Expected asymmetric landmark is missing or mirrored')
    return [min(p[0] for p in points),min(p[1] for p in points),
            max(p[0] for p in points)+1,max(p[1] for p in points)+1]


@unittest.skipUnless(os.environ.get('BLENDER_BIN'), 'Set BLENDER_BIN for real drawing integration')
class BlenderDrawingTest(unittest.TestCase):
    def test_three_views_have_actual_scale_preserve_source_and_repeat(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            create = root/'create.py'
            create.write_text('''import bpy
from pathlib import Path
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = .01
bpy.ops.mesh.primitive_cube_add()
bpy.context.object.name = 'Body'
bpy.context.object.scale = (1,.6,.4)
bpy.ops.mesh.primitive_cube_add(location=(.4,.1,.8))
bpy.context.object.name = 'TopPart'
bpy.context.object.scale = (.15,.15,.4)
bpy.ops.wm.save_as_mainfile(filepath=str(Path(__file__).parent/'source.blend'))
''', encoding='utf-8')
            result = subprocess.run([os.environ['BLENDER_BIN'], '--background', '--factory-startup',
                                     '--disable-autoexec', '--python-exit-code','1','--python',str(create)],
                                    capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            source, parts = root/'source.blend', root/'parts.json'
            parts.write_text(json.dumps({'body':['Body'], 'top-part':['TopPart']}))
            original = digest(source)
            try:
                first = generate(source,os.environ['BLENDER_BIN'],parts,root/'first',
                                 meters_per_pixel=.0001,resolution=384)
                for name, view in first['settings']['views'].items():
                    landmarks = {'front': [(232,112)], 'side': [(202,112)], 'top': []}[name]
                    actual = alpha_bounds(root/'first'/(name+'.png'), landmarks)
                    (left,bottom),(right,top) = view['bounds_px']
                    for value, expected in zip(actual, (left,top,right,bottom)):
                        self.assertAlmostEqual(value, expected, delta=3, msg=name)
                generate(source,os.environ['BLENDER_BIN'],parts,root/'second',
                         meters_per_pixel=.0001,resolution=384)
                for name in ('front','side','top'):
                    self.assertEqual(digest(root/'first'/(name+'.png')), digest(root/'second'/(name+'.png')))
                for name, sha in first['files'].items():
                    self.assertEqual(digest(root/'first'/name),sha)
                self.assertEqual(first['source_sha256'],original)
                self.assertEqual(digest(source),original)
                design=root/'reference.txt'
                design.write_text('Analytic fixture: Body is 20 x 12 x 8 mm; no production approval')
                provenance=dict(basis='observed',description='Analytic fixture definition',reference_ids=['design'])
                contract=dict(schema_version='shape-contract-v1',asset_id='synthetic-drawing',
                     design_revision='analytic-fixture',units='mm',
                     references={'design':dict(path='reference.txt',sha256=digest(design),view='text')},
                     parts={part:dict(objects=names,observations=[provenance])
                            for part,names in json.loads(parts.read_text()).items()},
                     dimensions={'body':dict(provenance,size=[20,12,8],tolerance=.001)},uncertainties=[])
                snapshot,_=verify_drawings(root/'first/manifest.json',original)
                report=evaluate(contract,snapshot,root)
                self.assertEqual(report['findings'],[])
                contract['dimensions']['body']['size']=[21,12,8]
                report=evaluate(contract,snapshot,root)
                self.assertEqual(report['findings'][0]['status'],'FAIL')
                (root/'first/shape-check.json').write_text(json.dumps(report,indent=2))
                with self.assertRaises(FileExistsError):
                    generate(source,os.environ['BLENDER_BIN'],parts,root/'first',meters_per_pixel=.0001)
            finally:
                if os.environ.get('DRAWING_ARTIFACT_DIR'):
                    destination = Path(os.environ['DRAWING_ARTIFACT_DIR'])
                    destination.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,destination/'source.blend')
                    shutil.copy2(parts,destination/'parts.json')
                    if (root/'first').exists():
                        shutil.copytree(root/'first',destination/'drawings',dirs_exist_ok=True)
