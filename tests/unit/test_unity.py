import copy
import unittest

from asset_pipeline.evidence import Evidence
from asset_pipeline.qa import evaluate
from asset_pipeline.specification import STAGES
from asset_pipeline.unity import export
from tests.fixtures.game_asset import CoreFixture


class UnityExportTest(unittest.TestCase):
    def setUp(self):
        self.snapshot=dict(source_sha256='a'*64,coordinate_space='world',
             scene_units=dict(system='METRIC',scale_length=.01),
             parts={'triangle':dict(vertices=[[0,0,0],[1,0,0],[0,1,0]],faces=[[0,1,2]],triangles=[[0,1,2]])})

    def test_axis_unit_conversion_and_handed_winding_preserve_input(self):
        frozen=copy.deepcopy(self.snapshot)
        actual=export(self.snapshot,'a'*64)
        self.assertEqual(actual['parts'][0]['vertices'][2],dict(x=0,y=0,z=.01))
        self.assertEqual(actual['parts'][0]['triangles'],[0,2,1])
        self.assertEqual(actual['bounds_max'],dict(x=.01,y=0,z=.01))
        self.assertEqual(self.snapshot,frozen)

    def test_stale_unknown_units_and_missing_actual_triangles_are_rejected(self):
        with self.assertRaises(ValueError):export(self.snapshot,'b'*64)
        self.snapshot['scene_units']['system']='NONE'
        with self.assertRaises(ValueError):export(self.snapshot,'a'*64)
        self.snapshot['scene_units']['system']='METRIC'
        self.snapshot['parts']['triangle']['triangles']=[[0,0,2]]
        with self.assertRaises(ValueError):export(self.snapshot,'a'*64)


class UnityBudgetTest(CoreFixture):
    def test_headless_smoke_cannot_be_used_as_runtime_budget_validation(self):
        self.run['stage']=STAGES[7]
        self.add_asset('engine-smoke.json','engine-report',dict(runtime_budget_verified=False))
        self.run['engine_report']='engine-smoke.json'
        with self.assertRaisesRegex(ValueError,'Headless smoke'):
            evaluate(self.run,Evidence(self.run,self.root))
