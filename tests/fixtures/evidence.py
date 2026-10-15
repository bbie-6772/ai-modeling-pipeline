"""Synthetic evidence fixture; never real human approval."""
import tempfile
from pathlib import Path
import unittest
from asset_pipeline.files import digest
from .surface import add_surface_fixture


class EvidenceFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        assets = []
        for role in ('design', 'reference', 'baseline', 'candidate', 'evidence'):
            path = self.root / (role + '.txt')
            path.write_text('synthetic ' + role, encoding='utf-8')
            assets.append({'role': role, 'path': path.name, 'sha256': digest(path)})
        self.config = {'project': 'example-asset-project', 'design_revision': 'design-v1', 'mode': 'validate-only',
                       'assets': assets, 'approval': {'status': 'approved',
                       'reviewer': 'synthetic-test-only', 'reviewed_at': '2026-10-15',
                       'bundle_sha256': ''}}
        add_surface_fixture(self.config, self.root)
