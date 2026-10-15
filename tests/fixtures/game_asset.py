"""Reusable synthetic run fixture, independent of test case modules."""
import copy
import json
import unittest
from asset_pipeline.files import digest
from asset_pipeline.evidence import run_digest
from asset_pipeline.specification import STAGES, CHECKS
from asset_pipeline.profiles import policy
from asset_pipeline.workflow import validate
from .surface import resign
from .evidence import EvidenceFixture


class CoreFixture(unittest.TestCase):
    def setUp(self):
        # Reuse, but do not edit, the preserved Surface Gate fixture.
        fixture = EvidenceFixture()
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
