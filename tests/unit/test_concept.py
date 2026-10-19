import json
from pathlib import Path
import tempfile
import unittest

from asset_pipeline.concept import prepare,register


class ConceptTest(unittest.TestCase):
    def test_candidate_and_draft_cannot_claim_approval_or_dimensions(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'concept'
            prepare(dict(asset_id='demo',design_revision='proposal',description='A storage prop',parts=['body'],constraints=[]),out)
            image=root/'image.png';image.write_bytes(b'\x89PNG\r\n\x1a\nSYNTHETIC TEST ONLY')
            result=register(out,image,'synthetic-test-provider')
            self.assertFalse(result['approved']);self.assertFalse(result['selected'])
            self.assertEqual(result['status'],'pending-human-review')
            draft=json.loads((out/'shape-draft.json').read_text())
            self.assertEqual(draft['dimensions']['body']['basis'],'unknown')
            self.assertIsNone(draft['dimensions']['body']['size'])
            with self.assertRaises(ValueError):register(out,image,'synthetic-test-provider')

    def test_changed_prompt_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'concept'
            prepare(dict(asset_id='demo',design_revision='proposal',description='A prop',parts=['body'],constraints=[]),out)
            (out/'prompt.txt').write_text('changed')
            with self.assertRaisesRegex(ValueError,'modified'):register(out,root/'not-needed.png','test-provider')
