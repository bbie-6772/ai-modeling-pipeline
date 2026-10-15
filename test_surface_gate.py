import copy
import json
import unittest

from pipeline import digest, validate
from surface_fixture import resign
from surface_gate import geometry_delta
import test_pipeline


class SurfaceGateTest(unittest.TestCase):
    setUp = test_pipeline.EvidenceGateTest.setUp
    def result(self):
        return validate(self.config, self.root)

    def rewrite(self, path, value):
        (self.root/path).write_text(json.dumps(value), encoding='utf-8')
        for asset in self.config['assets']:
            if asset['path'] == path:
                asset['sha256'] = digest(self.root/path)
        resign(self.config)

    def test_missing_gate_or_part_or_aspect_blocks_even_with_resigned_final(self):
        base = copy.deepcopy(self.config)
        mutations = [lambda c: c.pop('surface_review'), lambda c: c.pop('stage'),
                     lambda c: c.update(stage='blockout'), lambda c: c.update(scope=['body', 'arm']),
                     lambda c: c['surface_review'].update(blockout_is_proxy=False),
                     lambda c: c['surface_review']['parts'][0]['checks'].pop('curvature')]
        for mutate in mutations:
            self.config = copy.deepcopy(base)
            mutate(self.config)
            self.assertEqual(self.result()['status'], 'blocked')

    def test_pending_core_blocks_detail_even_with_final_approval(self):
        self.config['stage'] = 'detail-entry'
        self.config['surface_review']['approval']['status'] = 'pending'
        self.assertFalse(self.result()['detail_allowed'])
        self.assertTrue(self.result()['geometry_deltas']['body']['existing_surface_changed'])

    def test_detail_requires_core_but_final_approval_is_separate(self):
        self.config['stage'] = 'detail-entry'
        self.config['approval']['status'] = 'pending'
        self.assertTrue(self.result()['detail_allowed'])
        self.config['stage'] = 'final'
        self.assertEqual(self.result()['status'], 'blocked')

    def test_metadata_and_issue_changes_invalidate_core_approval(self):
        base = copy.deepcopy(self.config)
        mutations = [lambda c: c['surface_review']['parts'][0].update(decision_reason='new rationale'),
                     lambda c: c['surface_review']['parts'][0]['uncertainties'].append(
                         dict(description='hidden edge', reason='occluded', disposition='accepted-nonblocking'))]
        for mutate in mutations:
            self.config = copy.deepcopy(base)
            mutate(self.config)
            self.assertEqual(self.result()['status'], 'blocked')

    def test_unresolved_and_unknown_checks_block(self):
        part = self.config['surface_review']['parts'][0]
        for status in ('unknown', 'mismatch', 'pending'):
            part['checks']['depth']['status'] = status
            resign(self.config)
            self.assertFalse(self.result()['detail_allowed'])

    def test_blocking_issue_cannot_be_approved_away(self):
        self.config['surface_review']['parts'][0]['unresolved_differences'] = [
            dict(description='wrong anchor', reason='needs repair', disposition='blocking')]
        resign(self.config)
        self.assertFalse(self.result()['detail_allowed'])

    def test_explicit_nonblocking_uncertainty_requires_fresh_human_review(self):
        self.config['surface_review']['parts'][0]['uncertainties'] = [
            dict(description='hidden seam', reason='not visible in sources', disposition='accepted-nonblocking')]
        self.assertFalse(self.result()['detail_allowed'])
        resign(self.config)
        self.assertTrue(self.result()['detail_allowed'])

    def test_added_detail_does_not_count_as_surface_correction(self):
        before = json.loads((self.root/'before.json').read_text())
        after = json.loads((self.root/'after.json').read_text())
        after['parts'] = copy.deepcopy(before['parts'])
        after['parts']['body']['vertices'].extend([[2, 0, 0], [2, 1, 0], [2, 0, 1]])
        after['parts']['body']['faces'].append([3, 4, 5])
        self.rewrite('after.json', after)
        self.assertIn('added detail', self.result()['errors'][0])

    def test_retain_requires_unchanged_geometry_and_all_match(self):
        after = json.loads((self.root/'after.json').read_text())
        after['parts'] = json.loads((self.root/'before.json').read_text())['parts']
        self.rewrite('after.json', after)
        alignment = json.loads((self.root/'alignment.json').read_text())
        alignment['after']['geometry_sha256'] = digest(self.root/'after.json')
        self.rewrite('alignment.json', alignment)
        part = self.config['surface_review']['parts'][0]
        part['decision'] = 'retain'
        for check in part['checks'].values():
            check['status'] = 'match'
        resign(self.config)
        self.assertTrue(self.result()['detail_allowed'])
        part['checks']['depth']['status'] = 'corrected'
        resign(self.config)
        self.assertFalse(self.result()['detail_allowed'])

    def test_stale_geometry_and_camera_fitting_block(self):
        alignment = json.loads((self.root/'alignment.json').read_text())
        for field, value in [('camera', {'scale': 3}), ('geometry_sha256', '0'*64)]:
            changed = copy.deepcopy(alignment)
            changed['after'][field] = value
            self.rewrite('alignment.json', changed)
            self.assertFalse(self.result()['detail_allowed'])

    def test_snapshot_binding_and_nonfinite_geometry_block(self):
        after = json.loads((self.root/'after.json').read_text())
        for mutate in (lambda a: a.update(source_sha256='0'*64),
                       lambda a: a['parts']['body']['vertices'][0].__setitem__(0, float('nan'))):
            changed = copy.deepcopy(after)
            mutate(changed)
            self.rewrite('after.json', changed)
            self.assertFalse(self.result()['detail_allowed'])

    def test_rebuild_is_explicit_and_records_geometry_delta(self):
        self.config['surface_review']['parts'][0]['decision'] = 'rebuild'
        resign(self.config)
        result = self.result()
        self.assertTrue(result['detail_allowed'])
        self.assertEqual(result['geometry_deltas']['body']['removed_or_moved_vertices'], 1)

    def test_winding_change_counts_but_vertex_reindexing_does_not(self):
        before = dict(vertices=[[0, 0, 0], [1, 0, 0], [0, 1, 0]], faces=[[0, 1, 2]])
        reindexed = dict(vertices=[[1, 0, 0], [0, 1, 0], [0, 0, 0]], faces=[[2, 0, 1]])
        self.assertFalse(geometry_delta(before, reindexed)['changed'])
        flipped = dict(before, faces=[[2, 1, 0]])
        self.assertTrue(geometry_delta(before, flipped)['existing_surface_changed'])

    def test_core_statement_cannot_change_under_old_hash(self):
        self.config['surface_review']['approval']['statement'] = 'changed approval statement'
        self.assertFalse(self.result()['detail_allowed'])

    def test_unregistered_evidence_and_snapshot_outside_scope_block(self):
        self.config['surface_review']['parts'][0]['checks']['depth']['evidence'] = ['missing.png']
        resign(self.config)
        self.assertFalse(self.result()['detail_allowed'])
        self.config['surface_review']['parts'][0]['checks']['depth']['evidence'] = ['after.png']
        after = json.loads((self.root/'after.json').read_text())
        after['parts']['outside'] = after['parts']['body']
        self.rewrite('after.json', after)
        self.assertFalse(self.result()['detail_allowed'])

    def test_cli_valid_detail_entry_and_example_blocked(self):
        import subprocess
        import sys
        from pathlib import Path
        self.config['stage'] = 'detail-entry'
        path = self.root/'config.json'
        path.write_text(json.dumps(self.config), encoding='utf-8')
        cli = str(Path(__file__).with_name('pipeline.py'))
        result = subprocess.run([sys.executable, cli, str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(json.loads(result.stdout)['detail_allowed'])
        result = subprocess.run([sys.executable, cli, str(Path(cli).with_name('config.example.json'))], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)['detail_allowed'])


if __name__ == '__main__':
    unittest.main()
