"""Synthetic contract tests. Placeholder evidence is never real asset approval."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_pipeline
from pipeline import digest
from surface_fixture import resign
from asset_pipeline.evidence import run_digest
from asset_pipeline.specification import STAGES, CHECKS
from asset_pipeline.profiles import policy, PROFILE_PATH
from asset_pipeline.workflow import validate
from asset_pipeline.executor import execute
from asset_pipeline.blender_adapter import validate_plan


class CoreTest(unittest.TestCase):
    def setUp(self):
        # Reuse, but do not edit, the preserved Surface Gate fixture.
        fixture = test_pipeline.EvidenceGateTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = fixture.root
        self.legacy = fixture.config
        self.run = {
            'schema_version': '1.0', 'stage': STAGES[4],
            'specification': {
                'asset_id': 'synthetic-robot', 'project': self.legacy['project'],
                'design_revision': self.legacy['design_revision'], 'profile': 'machine-robot',
                'target_engine': 'synthetic-engine', 'units': 'm', 'scope': ['body'],
                'design_constraints': {'body': 'SYNTHETIC ONLY: depth 0.2'},
                'features': dict(deforming=False, repeated=True, collision=True, lod=True, textured=True),
                'budgets': dict(triangles=1000, materials=2, texture_mib=4, frame_ms=1)},
            'assets': copy.deepcopy(self.legacy['assets']),
            'baseline': 'baseline.txt', 'candidate': 'candidate.txt', 'design': 'design.txt',
            'references': ['reference.txt'], 'completed_stages': [],
            'operation': dict(parts=['body'], risk='low', changes_design=False, destructive=False, rebuild=False),
            'qa': {}, 'issues': [], 'revisions': [], 'approvals': [],
            'surface_review': copy.deepcopy(self.legacy['surface_review']),
            'metrics': dict(seconds={k: None for k in ('analysis', 'modeling', 'render', 'human_review', 'waiting', 'revision')},
                            tokens=None, human_revision_requests=None)}
        before = json.loads((self.root/'before.json').read_text())
        before.update(source_asset='baseline.txt', source_sha256=digest(self.root/'baseline.txt'))
        self.add_asset('baseline-snapshot.json', 'geometry', before)
        candidate_sha = digest(self.root/'candidate.txt')
        for check in CHECKS:
            self.run['qa'][check] = dict(status='UNKNOWN', observation='Not run')
        required, exceptions = policy(self.run['specification'])
        for check, record in self.run['qa'].items():
            if check in exceptions:
                record.update(status='N/A', reason=exceptions[check])
            elif not check.startswith('I'):
                record.update(status='PASS', method='synthetic fixture', evidence=['after.png'],
                              candidate_sha256=candidate_sha, coverage=['collision', 'lod'])
        regression = {k: dict(status=v['status'], candidate_sha256=candidate_sha,
                             evidence=['after.png']) for k, v in self.run['qa'].items()}
        self.run['revisions'] = [dict(id='r1', before_snapshot='baseline-snapshot.json', after_snapshot='after.json',
                                      parts=['body'], reason='Move primary face', regression=regression)]
        self.legacy['assets'] = self.run['assets']
        resign(self.legacy)
        self.run['surface_review'] = copy.deepcopy(self.legacy['surface_review'])
        self.stage(STAGES[4])

    def add_asset(self, path, role, value):
        (self.root/path).write_text(json.dumps(value), encoding='utf-8')
        self.run['assets'].append(dict(path=path, role=role, sha256=digest(self.root/path)))

    def stage(self, name):
        self.run['stage'] = name
        self.run['completed_stages'] = [dict(stage=s, summary='Synthetic completion only', evidence=['evidence.txt'])
                                        for s in STAGES[:STAGES.index(name)]]
        self.sign()

    def sign(self):
        self.run['approvals'] = [dict(kind=k, reviewer='SYNTHETIC ONLY', reviewed_at='2026-10-15',
                                     statement='Fixture, not human approval', evidence='human.txt', status='approved',
                                     bundle_sha256=run_digest(self.run))
                                for k in ('design-lock', 'operation-medium', 'operation-high', 'core-shape', 'final')]

    def blocked(self):
        self.assertEqual(validate(self.run, self.root)['status'], 'blocked')

    def test_valid_critique_does_not_claim_art_or_engine_success(self):
        result = validate(self.run, self.root)
        self.assertTrue(result['transition_allowed'], result)
        self.assertFalse(result['detail_allowed'])
        self.assertEqual(result['model_validation'], 'not_run')
        self.assertEqual(result['geometry_deltas'][0]['parts']['body']['removed_or_moved_vertices'], 1)
        self.assertIsNone(result['kpis']['tokens'])
        self.assertIsNone(result['kpis']['total_seconds'])
        self.assertEqual(result['kpis']['qa_coverage'], 13/15)

    def test_all_seven_profiles_cover_every_id_and_cannot_hide_required_checks(self):
        profiles = json.loads(PROFILE_PATH.read_text())
        self.assertEqual(len(profiles), 7)
        self.assertEqual(len(CHECKS), 16)
        for name in profiles:
            spec = copy.deepcopy(self.run['specification'])
            spec['profile'] = name
            for feature in spec['features']:
                spec['features'][feature] = False
            required, exceptions = policy(spec)
            self.assertEqual(required | set(exceptions), set(CHECKS))
            self.assertFalse(required & set(exceptions))
            self.assertIn('I01', required)
            spec['features']['lod'] = True
            self.assertIn('R03', policy(spec)[0])

    def test_profile_change_invalidates_approval(self):
        self.run['specification']['profile'] = 'prop'
        self.blocked()

    def test_design_scope_budget_feature_changes_stale_approval(self):
        original = copy.deepcopy(self.run)
        for key, value in [('design_revision', 'v2'), ('design_constraints', {'body': 'new design'}),
                           ('scope', ['body', 'extra']), ('budgets', dict(triangles=9, materials=1, texture_mib=1, frame_ms=1))]:
            self.run = copy.deepcopy(original)
            self.run['specification'][key] = value
            self.blocked()

    def test_stage_skip_and_reorder_block_even_if_resigned(self):
        self.run['completed_stages'].reverse()
        self.sign()
        self.blocked()

    def test_unknown_and_suspect_block_transition_but_allow_critique_repair(self):
        self.run['qa']['F01'] = dict(status='UNKNOWN', observation='Hidden silhouette')
        self.run['revisions'][0]['regression']['F01']['status'] = 'UNKNOWN'
        self.sign()
        result = validate(self.run, self.root)
        self.assertFalse(result['transition_allowed'])
        self.assertTrue(result['execution_allowed'])
        self.assertEqual(result['status'], 'needs-revision')
        self.run['qa']['F01'].update(status='SUSPECT', method='Synthetic observation',
                                      candidate_sha256=digest(self.root/'candidate.txt'), evidence=['after.png'])
        self.run['issues'] = [self.issue()]
        self.run['revisions'][0]['regression']['F01']['status'] = 'SUSPECT'
        self.sign()
        result = validate(self.run, self.root)
        self.assertTrue(result['execution_allowed'], result)
        self.assertFalse(result['transition_allowed'])

    def test_required_na_and_arbitrary_exception_rejected(self):
        self.run['qa']['F01'] = dict(status='N/A', observation='Skipped', reason='unneeded')
        self.sign()
        self.blocked()

    def test_fail_requires_issue_report(self):
        self.run['qa']['F01']['status'] = 'FAIL'
        self.run['revisions'][0]['regression']['F01']['status'] = 'FAIL'
        self.sign()
        self.blocked()

    def issue(self):
        return dict(id='i1', check='F01', part='body', region='face 0', severity='medium', status='open',
                    observation='Shape mismatch', expected='Approved primary face', evidence=['before.png'],
                    candidate='baseline.txt', candidate_sha256=digest(self.root/'baseline.txt'))

    def test_detect_diagnose_repair_verify_requires_complete_chain(self):
        issue = self.issue()
        self.run['issues'] = [issue]
        self.run['qa']['F01']['status'] = 'FAIL'
        self.run['revisions'][0]['regression']['F01']['status'] = 'FAIL'
        self.sign()
        result = validate(self.run, self.root)
        self.assertTrue(result['execution_allowed'], result)
        self.assertFalse(result['transition_allowed'])
        issue.update(status='diagnosed', diagnosis='Primary vertex depth incorrect')
        self.sign()
        self.assertEqual(validate(self.run, self.root)['status'], 'needs-revision')
        issue.update(status='repaired', repair='Move original vertex', repair_revision='r1')
        self.sign()
        self.assertEqual(validate(self.run, self.root)['status'], 'needs-revision')
        issue.update(status='verified', verification='Compare fixed view', verified_candidate='candidate.txt',
                     verification_evidence=['after.png'])
        self.run['qa']['F01']['status'] = 'PASS'
        self.run['revisions'][0]['regression']['F01']['status'] = 'PASS'
        self.sign()
        self.assertTrue(validate(self.run, self.root)['transition_allowed'])
        issue['verified_candidate'] = 'baseline.txt'
        self.sign()
        self.blocked()

    def test_missing_diagnosis_or_fake_repair_revision_blocks(self):
        issue = self.issue()
        self.run['issues'] = [issue]
        issue.update(status='verified', repair='Move vertex', repair_revision='made-up',
                     verification='Compared', verified_candidate='candidate.txt', verification_evidence=['after.png'])
        self.sign()
        self.blocked()
        issue['diagnosis'] = 'Wrong depth'
        self.sign()
        self.blocked()

    def test_risk_cannot_downgrade_rebuild_or_destructive_operation(self):
        self.run['operation']['rebuild'] = True
        self.sign()
        self.run['approvals'] = [a for a in self.run['approvals'] if a['kind'] != 'operation-medium']
        self.blocked()
        self.sign()
        self.assertEqual(validate(self.run, self.root)['risk'], 'medium')
        self.run['operation']['destructive'] = True
        self.sign()
        self.run['approvals'] = [a for a in self.run['approvals'] if a['kind'] != 'operation-high']
        self.blocked()

    def test_ai_cannot_change_locked_design_even_with_same_revision_and_new_approval(self):
        self.run['operation']['changes_design'] = True
        self.sign()
        self.blocked()

    def test_surface_gate_required_at_detail(self):
        self.stage(STAGES[5])
        result = validate(self.run, self.root)
        self.assertTrue(result['detail_allowed'], result)
        self.run['surface_review']['parts'][0]['checks']['depth']['status'] = 'unknown'
        self.sign()
        self.blocked()

    def test_detail_needs_core_approval_separate_from_final(self):
        self.stage(STAGES[5])
        self.run['approvals'] = [a for a in self.run['approvals'] if a['kind'] != 'core-shape']
        self.blocked()

    def test_geometry_history_actual_changes_scope_and_regression(self):
        event = self.run['revisions'][0]
        for field, value in [('parts', []), ('before_snapshot', 'after.json')]:
            original = event[field]
            event[field] = value
            self.sign()
            self.blocked()
            event[field] = original
        event['regression']['V01']['status'] = 'FAIL'
        self.sign()
        self.blocked()

    def test_history_cannot_be_omitted(self):
        self.run['revisions'] = []
        self.sign()
        self.blocked()

    def test_hash_and_path_tamper_fail_closed(self):
        self.run['assets'][0]['path'] = '../outside.txt'
        self.sign()
        self.blocked()

    def test_qa_stale_candidate_or_wrong_evidence_role_blocks(self):
        self.run['qa']['F01']['candidate_sha256'] = '0'*64
        self.sign()
        self.blocked()
        self.run['qa']['F01']['candidate_sha256'] = digest(self.root/'candidate.txt')
        self.run['qa']['F01']['evidence'] = ['design.txt']
        self.sign()
        self.blocked()

    def test_collision_and_lod_both_required(self):
        self.run['qa']['R03']['coverage'] = ['collision']
        self.sign()
        self.blocked()

    def engine(self):
        report = dict(engine='synthetic-engine', version='test', test_scene='synthetic',
                      candidate_sha256=digest(self.root/'candidate.txt'), import_ok=True, runtime_ok=True,
                      measurements=dict(triangles=100, materials=1, texture_mib=2, frame_ms=.2))
        self.add_asset('engine.json', 'engine-report', report)
        self.run['engine_report'] = 'engine.json'
        for check in ('I01', 'I02'):
            self.run['qa'][check].update(status='PASS', method='Synthetic engine report', evidence=['engine.json'],
                                          candidate_sha256=digest(self.root/'candidate.txt'))
            self.run['revisions'][0]['regression'][check].update(status='PASS', evidence=['engine.json'])
        # The legacy Surface Gate binds every registered file. Rebind fixture only.
        self.legacy['assets'] = self.run['assets']
        resign(self.legacy)
        self.run['surface_review'] = copy.deepcopy(self.legacy['surface_review'])
        self.stage(STAGES[7])

    def test_engine_report_required_and_budget_failure_blocks(self):
        self.stage(STAGES[7])
        self.assertFalse(validate(self.run, self.root)['transition_allowed'])
        self.engine()
        result = validate(self.run, self.root)
        self.assertTrue(result['transition_allowed'], result)
        report = json.loads((self.root/'engine.json').read_text())
        report['measurements']['triangles'] = 1001
        (self.root/'engine.json').write_text(json.dumps(report))
        for a in self.run['assets']:
            if a['path'] == 'engine.json':
                a['sha256'] = digest(self.root/'engine.json')
        self.sign()
        self.blocked()

    def test_kpi_unknown_is_not_zero_and_values_must_be_measured(self):
        self.run['metrics']['tokens'] = 100
        self.sign()
        self.blocked()
        self.run['metrics']['token_source'] = 'synthetic usage fixture'
        self.run['metrics']['seconds'] = {k: 2 for k in self.run['metrics']['seconds']}
        self.sign()
        result = validate(self.run, self.root)
        self.assertEqual(result['kpis']['total_seconds'], 12)
        self.assertEqual(result['kpis']['tokens'], 100)
        self.run['metrics']['seconds']['render'] = float('nan')
        self.blocked()

    def test_executor_new_candidate_receipt_preserves_all_inputs(self):
        before = {p: p.read_bytes() for p in self.root.iterdir()}
        def adapter(path, parts):
            self.assertEqual(parts, ('body',))
            path.write_text('synthetic candidate edit')
        result = execute(self.run, self.root, 'new/candidate.txt', adapter)
        self.assertEqual(result['status'], 'candidate-pending-qa')
        self.assertFalse(result['adopted'])
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertTrue((self.root/'new/candidate.txt.receipt.json').is_file())
        with self.assertRaises(ValueError):
            execute(self.run, self.root, 'new/candidate.txt', adapter)

    def test_executor_blocked_gate_never_calls_adapter(self):
        self.run['approvals'] = []
        called = []
        with self.assertRaises(ValueError):
            execute(self.run, self.root, 'new.txt', lambda *a: called.append(a))
        self.assertEqual(called, [])
        self.assertFalse((self.root/'new.txt').exists())

    def test_executor_failure_preserves_candidate_without_adoption(self):
        def fail(path, parts):
            raise RuntimeError('Synthetic adapter failure')
        result = execute(self.run, self.root, 'failed.txt', fail)
        self.assertEqual(result['status'], 'adapter-failed')
        self.assertFalse(result['adopted'])
        self.assertTrue((self.root/'failed.txt').exists())

    def test_executor_rejects_existing_or_outside_path(self):
        for path in ('baseline.txt', '../escaped.txt', str(self.root/'absolute.txt')):
            with self.assertRaises(ValueError):
                execute(self.run, self.root, path, lambda *a: None)

    def test_executor_detects_protected_input_modification(self):
        def bad_adapter(path, parts):
            (self.root/'baseline.txt').write_text('tamper')
        with self.assertRaisesRegex(ValueError, 'protected input'):
            execute(self.run, self.root, 'bad.txt', bad_adapter)

    def test_malformed_inputs_fail_closed(self):
        for run in (None, [], {}, {'schema_version': '2.0'}):
            self.assertEqual(validate(run, self.root)['status'], 'blocked')

    def test_cli_success_and_blocked_template(self):
        path = self.root/'run.json'
        path.write_text(json.dumps(self.run), encoding='utf-8')
        args = [sys.executable, '-m', 'asset_pipeline', str(path)]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path.write_text('{', encoding='utf-8')
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)['execution_allowed'])

    def test_blender_plan_is_bounded_and_rejects_bad_geometry(self):
        good = dict(kind='vertex-edits-v1', parts={'body': ['Body']},
                    edits=[dict(object='Body', vertex=0, position=[0, 0, .2])])
        validate_plan(good, ['body'])
        for field, value in [('object', 'Protected'), ('vertex', -1), ('vertex', True),
                             ('position', [0, float('inf'), 0]), ('position', [0, 1])]:
            plan = copy.deepcopy(good)
            plan['edits'][0][field] = value
            with self.assertRaises(ValueError):
                validate_plan(plan, ['body'])
        with self.assertRaises(ValueError):
            validate_plan(good, ['other-part'])

    def test_issue_severity_cannot_bypass_human_risk_approval(self):
        issue = self.issue()
        issue['severity'] = 'high'
        self.run['issues'] = [issue]
        self.sign()
        self.run['approvals'] = [a for a in self.run['approvals'] if a['kind'] != 'operation-high']
        self.blocked()
        self.sign()
        self.assertEqual(validate(self.run, self.root)['risk'], 'high')

    def test_variant_c_is_a_profile_case_and_template_is_not_an_approval(self):
        historical = json.loads((Path(__file__).parent/'examples/minor-on-air/legacy-variant-c.config.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(historical['variant'], 'C')
        self.assertEqual(historical['project'], 'Minor On Air')
        self.assertEqual(historical['approval']['status'], 'pending')
        template = json.loads((Path(__file__).parent/'examples/minor-on-air/variant-c.run.example.json').read_text())
        self.assertEqual(template['specification']['profile'], 'machine-robot')
        self.assertEqual(template['approvals'], [])
        self.assertEqual(validate(template, self.root)['status'], 'blocked')
        self.run['specification']['design_revision'] = 'variant-c-approved-SYNTHETIC-ONLY'
        self.sign()
        self.assertTrue(validate(self.run, self.root)['transition_allowed'])
        self.assertEqual(test_pipeline.validate(self.legacy, self.root)['status'], 'evidence-consistent')
        self.run['specification']['design_revision'] = 'variant-b-unapproved'
        self.blocked()
        self.run['specification']['design_revision'] = 'variant-c-approved-SYNTHETIC-ONLY'
        (self.root/'baseline.txt').write_text('tampered Variant C baseline')
        self.blocked()


if __name__ == '__main__':
    unittest.main()
