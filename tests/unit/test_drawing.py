import copy
import unittest
from xml.etree import ElementTree

from asset_pipeline.drawing import layout, panel


def cube():
    return dict(vertices=[[x,y,z] for z in (0,1) for y in (0,1) for x in (0,1)],
                faces=[[0,2,3,1],[4,5,7,6],[0,1,5,4],[2,6,7,3],[0,4,6,2],[1,3,7,5]])


class DrawingTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = dict(scene_units=dict(system='METRIC', scale_length=.01),
                             parts={'body': cube()})

    def test_one_physical_scale_and_registration_across_views(self):
        frozen = copy.deepcopy(self.snapshot)
        result = layout(self.snapshot, .0001, 256, [0,0,0], 'mm')
        self.assertEqual(result['bounds_m'], [[0,0,0],[.01,.01,.01]])
        for view in result['views'].values():
            self.assertEqual(view['dimensions'], [10,10])
            self.assertEqual(view['origin_px'], [128,128])
            self.assertAlmostEqual(view['ortho_scale_m'], .0256)
            self.assertEqual(view['bounds_px'], [[128,128],[228,28]])
        self.assertEqual(self.snapshot, frozen)

    def test_fixed_framing_never_silently_fits_model(self):
        with self.assertRaisesRegex(ValueError, 'fixed framing'):
            layout(self.snapshot, .00001, 256, [0,0,0], 'mm')
        with self.assertRaisesRegex(ValueError, 'physical scene'):
            layout(dict(self.snapshot, scene_units={'system':'NONE','scale_length':1}), .01,256,[0,0,0],'m')

    def test_svg_dimensions_and_labels_are_escaped(self):
        self.snapshot['parts'] = {'part<&': cube()}
        settings = layout(self.snapshot, .0001, 256, [0,0,0], 'mm')
        svg = panel('front', settings['views']['front'], settings, b'PNG-placeholder')
        ElementTree.fromstring(svg)
        self.assertIn('X 10 mm', svg)
        self.assertIn('Z 10 mm', svg)
        self.assertIn('part&lt;&amp;', svg)
        self.assertIn('data:image/png;base64,', svg)
