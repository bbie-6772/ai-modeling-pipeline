import copy
import json

from asset_pipeline.drawing import layout
from asset_pipeline.files import digest
from asset_pipeline.shape_contract import evaluate,verify_drawings
from asset_pipeline.workflow import validate
from tests.fixtures.game_asset import CoreFixture
from tests.fixtures.shape import contract


class ShapeContractTest(CoreFixture):
    def setUp(self):
        super().setUp()
        self.snapshot=json.loads((self.root/'after.json').read_text())
        self.snapshot.update(scene_units=dict(system='METRIC',scale_length=1),frame=1)
        self.snapshot['parts']['body']['objects']=['Body']
        path=self.root/'after.json'
        path.write_text(json.dumps(self.snapshot))
        for asset in self.run['assets']:
            if asset['path']=='after.json':asset['sha256']=digest(path)
        self.contract=contract(digest(self.root/'reference.txt'))
        self.contract['asset_id']=self.run['specification']['asset_id']
        self.contract['design_revision']=self.run['specification']['design_revision']

    def bundle(self):
        folder=self.root/'drawings';folder.mkdir()
        self.add_asset('drawings/snapshot.json','geometry',self.snapshot)
        self.add_asset('drawings/parts.json','measurement',{'body':['Body']})
        settings=layout(self.snapshot,.01,256,[0,0,0],'m')
        self.add_asset('drawings/render-config.json','measurement',settings)
        for name in ('front.png','front.svg','side.png','side.svg','top.png','top.svg','sheet.svg'):
            self.add_asset('drawings/'+name,'render','SYNTHETIC placeholder, not a real render')
        files={p.name:digest(p) for p in folder.iterdir()}
        self.add_asset('drawings/manifest.json','drawing-manifest',dict(kind='orthographic-drawings-v1',
                       source_sha256=digest(self.root/self.run['candidate']),files=files,settings=settings))
        self.add_asset('shape.json','shape-contract',self.contract)
        self.run.update(shape_contract='shape.json',drawing_manifest='drawings/manifest.json')
        self.sign()

    def test_observed_dimensions_and_mismatch(self):
        self.assertEqual(evaluate(self.contract,self.snapshot,self.root)['findings'],[])
        self.contract['dimensions']['body']['size']=[2,1,.2]
        result=evaluate(self.contract,self.snapshot,self.root)
        self.assertEqual(result['findings'][0]['status'],'FAIL')
        self.assertEqual(result['approval'],'not_granted')

    def test_inferred_and_unknown_values_never_become_pass(self):
        for basis in ('inferred','unknown'):
            with self.subTest(basis=basis):
                value=copy.deepcopy(self.contract)
                value['dimensions']['body'].update(basis=basis,size=None)
                self.assertEqual(evaluate(value,self.snapshot,self.root)['findings'][0]['status'],'UNKNOWN')

    def test_missing_parts_bad_references_and_blocking_uncertainty(self):
        value=copy.deepcopy(self.contract);value['parts']={}
        with self.assertRaises(ValueError):evaluate(value,self.snapshot,self.root)
        value=copy.deepcopy(self.contract);value['references']['design']['sha256']='0'*64
        with self.assertRaises(ValueError):evaluate(value,self.snapshot,self.root)
        self.contract['uncertainties']=[dict(part='body',description='Hidden depth not established',blocking=True)]
        self.assertTrue(evaluate(self.contract,self.snapshot,self.root)['findings'])

    def test_low_iou_blocks_without_a_manual_pass_override(self):
        self.contract['outlines']=[dict(self.contract['dimensions']['body'],part='body',view='top',
                meters_per_pixel=.01,origin_px=[10000,100],points=[[0,100],[100,100],[100,0],[0,0]],minimum_iou=.9)]
        result=evaluate(self.contract,self.snapshot,self.root)
        self.assertEqual(next(f for f in result['findings'] if f['check']=='F01')['status'],'FAIL')

    def test_bundle_and_core_binding_and_fail_closed(self):
        self.bundle()
        self.assertTrue(validate(self.run,self.root)['transition_allowed'])
        self.contract['dimensions']['body']['size']=[2,1,.2]
        path=self.root/'shape.json';path.write_text(json.dumps(self.contract))
        for asset in self.run['assets']:
            if asset['path']=='shape.json':asset['sha256']=digest(path)
        self.sign()
        result=validate(self.run,self.root)
        self.assertEqual(result['errors'],[])
        self.assertFalse(result['transition_allowed'])
        self.assertEqual(result['shape_contract']['status'],'needs-review')
        (self.root/'drawings/front.png').write_text('tampered')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            verify_drawings(self.root/'drawings/manifest.json',digest(self.root/self.run['candidate']))

    def test_stale_candidate_and_fitted_camera_are_rejected(self):
        self.bundle()
        with self.assertRaises(ValueError):verify_drawings(self.root/'drawings/manifest.json','0'*64)
        path=self.root/'drawings/manifest.json';manifest=json.loads(path.read_text())
        manifest['settings']['views']['front']['ortho_scale_m']*=2
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'camera or scale'):
            verify_drawings(path,digest(self.root/self.run['candidate']))
