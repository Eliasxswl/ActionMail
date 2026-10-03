import shutil
import json
import tempfile
import unittest
from scripted_responses import explained
from pathlib import Path

from actionmail.evaluation.challenge import load_challenge
from actionmail.evaluation.suite import load_suite
from actionmail.evaluation.cli import PROJECT_ROOT, DEFAULT_MAILEX_ROOT
from actionmail.evaluation.review import ReviewDataset

MANIFEST = PROJECT_ROOT / 'evaluation/supplement_v2_approved.jsonl'


class SupplementTests(unittest.TestCase):
    def test_active_suite_hashes_and_saved_original_pdf(self):
        registry = PROJECT_ROOT / 'evaluation/active_suite.json'
        cases = load_suite(registry, DEFAULT_MAILEX_ROOT)
        self.assertEqual(len({c.case_id for c in cases}), 60)
        self.assertTrue(all(c.record.get('review_state', 'approved') == 'approved' for c in cases))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'saved'
            shutil.copytree(PROJECT_ROOT / 'results/evaluation/v2-regression-repair-20261001', output)
            dataset = ReviewDataset.open(output, registry, DEFAULT_MAILEX_ROOT)
            detail = dataset.detail('S03')
            self.assertIsNone(detail['email']['received_at'])
            self.assertGreater(len(detail['external_sources'][0]['text']), 3000)
            original, media = dataset.attachment('S03', 'attachment:1')
            self.assertTrue(original.startswith(b'%PDF-'))
            self.assertEqual(media, 'application/pdf')
            for sid in ('../../secret', 'link:1', 'attachment:999'):
                with self.assertRaises(KeyError): dataset.attachment('S03', sid)




    def test_informational_pdf_does_not_enter_model_context_but_required_workbook_does(self):
        from actionmail.workflow.multi_pipeline import process_email_multi_with_external
        from actionmail.reasoning.model_client import ModelReply
        cases = {c.case_id: c for c in load_challenge(MANIFEST, DEFAULT_MAILEX_ROOT, benchmark='supplement-v2')}
        class Model:
            def __init__(self, values):
                self.values = iter(values)
                self.prompts = []
            def complete(self, system, user):
                self.prompts.append(user)
                return ModelReply(json.dumps(explained(next(self.values), user)), 'offline', 10, 10, 1)
        case = cases['S03']
        model = Model([{'sources': [{'source_id': 'attachment:1', 'relevance': 'irrelevant', 'reason': 'The body is an informative balance update with no task dependent on the PDF.'}]}, case.gold])
        run = process_email_multi_with_external(case.email, model)
        self.assertEqual(run.decision.status, 'no_action')
        self.assertFalse(run.read_records)
        self.assertTrue(all('SOURCE attachment:1' not in prompt for prompt in model.prompts))
        case = cases['S08']
        model = Model([{'sources': [{'source_id': 'attachment:1', 'relevance': 'decisive', 'reason': 'The body explicitly assigns the task in the workbook.'}]}])
        run = process_email_multi_with_external(case.email, model)
        self.assertEqual(run.decision.status, 'needs_review')
        self.assertTrue(run.read_failures)
        self.assertEqual(len(model.prompts), 1)

    def test_export_target_must_be_an_actual_recipient(self):
        records = [json.loads(line) for line in MANIFEST.read_text(encoding='utf-8').splitlines()]
        records[2]['source']['target_recipient'] = 'invented@example.com'
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'bad.jsonl'
            manifest.write_text(''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Target absent'):
                load_challenge(manifest, DEFAULT_MAILEX_ROOT, benchmark='supplement-v2')
