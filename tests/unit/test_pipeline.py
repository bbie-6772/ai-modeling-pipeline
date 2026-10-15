import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from pipeline import digest, validate
from tests.fixtures.surface import resign
from tests.fixtures.evidence import EvidenceFixture


class EvidenceGateTest(EvidenceFixture):
    def test_consistent_bundle_does_not_claim_model_success(self):
        before = {p: p.read_bytes() for p in self.root.iterdir()}
        result = validate(self.config, self.root)
        self.assertEqual(result['status'], 'evidence-consistent')
        self.assertEqual(result['design_conformance'], 'not_evaluated')
        self.assertEqual(result['model_validation'], 'not_run')
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.iterdir()})

    def test_reject_invalid_inputs(self):
        cases = []
        for key, value in [('project', ''), ('project', None), ('design_revision', ''),
                           ('design_revision', 'design-v2'), ('mode', 'apply'), ('assets', [])]:
            c = copy.deepcopy(self.config)
            c[key] = value
            cases.append(c)
        for field, value in [('status', 'pending'), ('reviewer', ''), ('bundle_sha256', '0'*64)]:
            c = copy.deepcopy(self.config)
            c['approval'][field] = value
            cases.append(c)
        for value in ['../outside.txt', str(self.root.resolve()), 'missing.txt']:
            c = copy.deepcopy(self.config)
            c['assets'][0]['path'] = value
            cases.append(c)
        cases.extend([{}, None, [], {'project': None}])
        for c in cases:
            with self.subTest(config=c):
                self.assertEqual(validate(c, self.root)['status'], 'blocked')

    def test_approval_is_bound_to_project_and_design(self):
        for field, value in [('project', 'another-project'), ('design_revision', 'design-v2')]:
            altered = copy.deepcopy(self.config)
            altered[field] = value
            self.assertEqual(validate(altered, self.root)['status'], 'blocked')

    def test_any_named_project_and_revision_can_be_reviewed(self):
        self.config.update(project='Furniture', design_revision='chair-v4')
        resign(self.config)
        self.assertEqual(validate(self.config, self.root)['status'], 'evidence-consistent')

    def test_detect_tamper_and_duplicate(self):
        (self.root / 'baseline.txt').write_text('changed')
        self.assertEqual(validate(self.config, self.root)['status'], 'blocked')
        self.config['assets'][2]['sha256'] = digest(self.root / 'baseline.txt')
        self.assertEqual(validate(self.config, self.root)['status'], 'blocked')
        self.config['assets'].append(self.config['assets'][0])
        self.assertEqual(validate(self.config, self.root)['status'], 'blocked')

    def test_cli_malformed_json(self):
        path = self.root / 'bad.json'
        path.write_text('{')
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[2] / 'pipeline.py'), str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()
