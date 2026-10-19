"""Measurements are evidence; only a proven violation against a PASS becomes a finding."""
import unittest
import json

from asset_pipeline.measure import contradictions, measure, silhouette
from asset_pipeline.workflow import validate
from asset_pipeline.files import digest
from tests.fixtures.game_asset import CoreFixture


def cube(x=0, y=0, z=0):
    vertices = [[x + i, y + j, z + k] for k in (0, 1) for j in (0, 1) for i in (0, 1)]
    faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    return dict(vertices=vertices, faces=faces)


def results(spec, parts):
    return [(m['kind'], m['part'], m['result']) for m in measured(spec, parts)]


def measured(spec, parts):
    return measure(dict(units='m', **spec), parts, scene_units={'system': 'METRIC', 'scale_length': 1})


class MeasureTest(unittest.TestCase):
    def test_dimensions_use_world_extents_and_tolerance(self):
        parts = {'a': cube()}
        ok = {'dimensions': {'a': {'size': [1, 1, 1], 'tolerance': .001}}}
        bad = {'dimensions': {'a': {'size': [1, 1, 1.01], 'tolerance': .001}}}
        self.assertEqual(results(ok, parts), [('dimensions', 'a', 'within')])
        self.assertEqual(results(bad, parts), [('dimensions', 'a', 'outside')])

    def test_declared_mirror_and_offset_copies_are_verified(self):
        parts = {'left': cube(1), 'right': cube(-2), 'copy': cube(3), 'a': cube()}
        spec = {'features': {'repeated': True},
                'symmetry': {'left': {'of': 'right', 'mirror': 'x', 'plane': 0, 'tolerance': .001},
                             'copy': {'of': 'a', 'offset': [3, 0, 0], 'tolerance': .001}}}
        self.assertEqual(results(spec, parts), [('symmetry', 'left', 'within'), ('symmetry', 'copy', 'within')])
        parts['left']['vertices'][0][0] += .01
        self.assertEqual(measured(spec, parts)[0]['value'], 2)  # one stray vertex on each side
        self.assertEqual(results(spec, parts)[0][2], 'outside')

    def test_symmetry_declaration_must_be_unambiguous_and_applicable(self):
        rule = {'of': 'a', 'mirror': 'x', 'plane': 0, 'offset': [1, 0, 0], 'tolerance': .001}
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            measured({'features': {'repeated': True}, 'symmetry': {'a': rule}}, {'a': cube()})
        with self.assertRaisesRegex(ValueError, 'repeated feature'):
            measured({'features': {'repeated': False}, 'symmetry': {'a': dict(rule, offset=None)}}, {'a': cube()})

    def test_equivalent_physical_geometry_across_scene_and_spec_units(self):
        outline = dict(part='a', view='top', meters_per_pixel=.0001, origin_px=[0, 100],
                       points=[[0, 100], [100, 100], [100, 0], [0, 0]])
        for unit, size in (('m', .01), ('cm', 1), ('mm', 10)):
            for scale, extent in ((1, .01), (.01, 1)):
                with self.subTest(unit=unit, scale=scale):
                    parts = {'a': cube(), 'b': cube(3)}
                    for record in parts.values():
                        record['vertices'] = [[c * extent for c in v] for v in record['vertices']]
                    spec = dict(units=unit, features={'repeated': True},
                                dimensions={'a': dict(size=[size]*3, tolerance=size*.001)},
                                symmetry={'b': dict(of='a', offset=[size*3, 0, 0], tolerance=size*.001)},
                                anchors=[dict(part='a', to='b', relation='clearance', distance=size*1.5)])
                    actual = measure(spec, parts, [outline], {'system': 'METRIC', 'scale_length': scale})
                    self.assertEqual([m['result'] for m in actual[:3]], ['within']*3)
                    for value in actual[0]['value']:
                        self.assertAlmostEqual(value, size)
                    self.assertAlmostEqual(actual[2]['value'], size*2)
                    self.assertGreater(actual[3]['value'], .98)

    def test_measurements_require_supported_units_and_physical_scale(self):
        spec = dict(units='m', dimensions={'a': dict(size=[1]*3, tolerance=.001)})
        for units in (None, {}, {'system': 'NONE', 'scale_length': 1},
                      *({'system': 'METRIC', 'scale_length': value}
                        for value in (0, -1, True, float('nan'), float('inf')))):
            with self.subTest(scene_units=units), self.assertRaises(ValueError):
                measure(spec, {'a': cube()}, scene_units=units)
        with self.assertRaises(ValueError):
            measure(dict(spec, units='unknown'), {'a': cube()},
                    scene_units={'system': 'METRIC', 'scale_length': 1})
        self.assertEqual(measure({'units': 'm'}, {'a': cube()}), [])

    def test_anchor_boxes_prove_only_one_direction(self):
        parts = {'body': cube(), 'lid': cube(z=1), 'handle': cube(z=2.5)}
        spec = {'anchors': [dict(part='lid', to='body', relation='contact', distance=.001),
                            dict(part='handle', to='body', relation='contact', distance=.001),
                            dict(part='handle', to='body', relation='clearance', distance=1),
                            dict(part='handle', to='body', relation='clearance', distance=2)]}
        self.assertEqual([r[2] for r in results(spec, parts)], ['unknown', 'outside', 'within', 'unknown'])

    def test_silhouette_uses_recorded_placement_not_box_fitting(self):
        parts = {'a': cube()}
        square = dict(part='a', view='top', meters_per_pixel=.01, origin_px=[0, 100],
                      points=[[0, 100], [100, 100], [100, 0], [0, 0]])
        self.assertGreater(silhouette(square, parts), .98)
        self.assertAlmostEqual(silhouette(dict(square, origin_px=[50, 100]), parts), 1 / 3, delta=.02)

    def test_only_outside_contradicting_pass_is_a_finding(self):
        measured = [dict(check='F02', kind='dimensions', part='a', result='outside'),
                    dict(check='F04', kind='anchor-contact', part='a', result='unknown')]
        self.assertEqual(len(contradictions(measured, {'F02': {'status': 'PASS'}, 'F04': {'status': 'PASS'}})), 1)
        self.assertEqual(contradictions(measured, {'F02': {'status': 'FAIL'}, 'F04': {'status': 'PASS'}}), [])


class MeasuredRunTest(CoreFixture):
    def set_snapshot_units(self, units):
        path = self.root/'after.json'
        snapshot = json.loads(path.read_text())
        snapshot['scene_units'] = units
        path.write_text(json.dumps(snapshot), encoding='utf-8')
        for asset in self.run['assets']:
            if asset['path'] == 'after.json':
                asset['sha256'] = digest(path)

    def test_measured_violation_blocks_a_contradicting_pass(self):
        self.set_snapshot_units({'system': 'METRIC', 'scale_length': 1})
        self.run['specification']['dimensions'] = {'body': {'size': [1, 1, .3], 'tolerance': .01}}
        self.add_asset('outline.json', 'reference-outline', dict(
            part='body', view='top', meters_per_pixel=.01, origin_px=[0, 100], points=[[0, 100], [100, 100], [0, 0]]))
        self.run['outlines'] = ['outline.json']
        self.sign()
        result = validate(self.run, self.root)
        self.assertEqual(result['errors'], [])
        self.assertIn(dict(check='F02', status='PASS', measurement='dimensions', part='body'), result['findings'])
        self.assertFalse(result['transition_allowed'])
        self.assertGreater(next(m['value'] for m in result['measurements'] if m['kind'] == 'silhouette-top'), .9)

    def test_scaled_snapshot_cannot_pass_raw_world_dimensions(self):
        self.set_snapshot_units({'system': 'METRIC', 'scale_length': .01})
        self.run['specification']['dimensions'] = {'body': dict(size=[1, 1, .2], tolerance=.001)}
        self.sign()
        result = validate(self.run, self.root)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['measurements'][0]['result'], 'outside')
        self.assertFalse(result['transition_allowed'])
        self.run['specification']['dimensions']['body']['size'] = [.01, .01, .002]
        self.sign()
        result = validate(self.run, self.root)
        self.assertEqual(result['errors'], [])
        self.assertTrue(result['transition_allowed'])

    def test_missing_snapshot_units_and_unsupported_spec_units_block(self):
        self.run['specification']['dimensions'] = {'body': dict(size=[1, 1, .2], tolerance=.001)}
        self.sign()
        result = validate(self.run, self.root)
        self.assertFalse(result['transition_allowed'])
        self.assertIn('physical scene_units', result['errors'][0])
        self.run['specification']['units'] = 'unknown'
        self.sign()
        result = validate(self.run, self.root)
        self.assertIn('Supported specification units', result['errors'][0])


if __name__ == "__main__":
    unittest.main()
