import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from actionmail.evaluation.cases import load_cases
from actionmail.evaluation.challenge import load_challenge, prepare_challenge
from actionmail.evaluation.cli import PROJECT_ROOT, DEFAULT_MAILEX_ROOT
from actionmail.evaluation.review import ReviewDataset

MANIFEST = PROJECT_ROOT / 'evaluation/supplement_v2.jsonl'


class SupplementTests(unittest.TestCase):
    def test_sixty_distinct_cases_and_reviewable_real_pdf_without_invented_date(self):
        base = load_cases(PROJECT_ROOT / 'evaluation/cases.jsonl', DEFAULT_MAILEX_ROOT)
        extra = load_challenge(MANIFEST, DEFAULT_MAILEX_ROOT, benchmark='supplement-v2')
        self.assertEqual(len(base) + len(extra), 60)
        self.assertEqual(len({c.case_id for c in [*base, *extra]}), 60)
        suite = json.loads((PROJECT_ROOT / 'evaluation/active_suite.json').read_text(encoding='utf-8'))
        self.assertEqual(suite['total_cases'], 60)
        for component in suite['components']:
            path = PROJECT_ROOT / 'evaluation' / component['manifest']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), component['sha256'])
        self.assertTrue(all(c.record['review_state'] == 'pending_owner' for c in extra))
        self.assertIsNone(extra[2].email.received_at)
        self.assertEqual(len(extra[2].email.external_sources), 1)
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / 'preview'
            prepare_challenge(extra, MANIFEST, run, benchmark='supplement-v2')
            dataset = ReviewDataset.open(run, MANIFEST, DEFAULT_MAILEX_ROOT)
            detail = dataset.detail('S03')
            self.assertIsNone(detail['prediction'])
            self.assertEqual(detail['email']['source_kind'], 'enron_export')
            self.assertGreater(len(detail['external_sources'][0]['text']), 3000)
            self.assertFalse(detail['external_sources'][0]['read_by_model'])

    def test_export_target_must_be_an_actual_recipient(self):
        records = [json.loads(line) for line in MANIFEST.read_text(encoding='utf-8').splitlines()]
        records[2]['source']['target_recipient'] = 'invented@example.com'
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'bad.jsonl'
            manifest.write_text(''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Target absent'):
                load_challenge(manifest, DEFAULT_MAILEX_ROOT, benchmark='supplement-v2')
