import json
import hashlib
import tempfile
import unittest
from scripted_responses import explained
from pathlib import Path

from actionmail.evaluation.cases import load_cases
from actionmail.evaluation.challenge import load_challenge, prepare_challenge
from actionmail.evaluation.cli import PROJECT_ROOT, DEFAULT_MAILEX_ROOT
from actionmail.evaluation.review import ReviewDataset

MANIFEST = PROJECT_ROOT / 'evaluation/supplement_v2_revision2.jsonl'


class SupplementTests(unittest.TestCase):
    def test_active_suite_preview_and_full_reference_metrics(self):
        from actionmail.evaluation.suite import load_suite
        from actionmail.evaluation.cli import _run_one
        registry = PROJECT_ROOT / 'evaluation/active_suite.json'
        cases = load_suite(registry, DEFAULT_MAILEX_ROOT)
        self.assertEqual(len(cases), 60)
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / 'suite'
            prepare_challenge(cases, registry, run, benchmark='v2-60')
            dataset = ReviewDataset.open(run, registry, DEFAULT_MAILEX_ROOT)
            overview = dataset.overview()['cases']
            self.assertEqual(len(overview), 60)
            self.assertEqual(sum(c['group'] == 'base' for c in overview), 50)
            self.assertTrue(all(c['predicted_status'] == 'pending' for c in overview))
            self.assertIn('dennis_mcconaghy@transcanada.com', next(c for c in overview if c['case_id'] == 'S01')['search_text'])
            self.assertIsNone(dataset.detail(cases[0].case_id)['prediction'])
            self.assertEqual(dataset.detail('S09')['email']['target_recipient'], 'alex@example.com')
        # The full suite scores established base labels rather than treating them as pending multi-action drafts.
        from actionmail.reasoning.model_client import ModelReply
        case = next(c for c in cases if not c.record.get('challenge_version') and c.gold['status'] == 'action')
        class Model:
            def complete(self, system, user):
                result = {'status': 'action', 'actions': [{'kind': 'perform_task', 'text': case.gold['action'], 'deadline': case.gold['deadline'], 'evidence': case.gold['evidence']}], 'reason': 'The email requests this task.', 'evidence': case.gold['evidence']}
                return ModelReply(json.dumps(result), 'offline', 10, 10, 1)
        row = _run_one(case, 'llm', Model(), (0, 0, 0), schema='v2', score_frozen=True)
        self.assertTrue(row['status_correct'])
        self.assertTrue(row['action_count_match'])

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
            saved = dataset.save_review('S03', {'gold_label': 'correct', 'model_pass': 'uncertain', 'note': 'Check only the overall pass.'})
            self.assertEqual(saved['model_pass'], 'uncertain')
            self.assertEqual(saved['action_meaning'], '')
            self.assertIn('/attachments/', detail['external_sources'][0]['original_attachment_url'])
            original, media = dataset.attachment('S03', 'attachment:1')
            self.assertTrue(original.startswith(b'%PDF-'))
            self.assertEqual(media, 'application/pdf')
            for sid in ('../../secret', 'link:1', 'attachment:999'):
                with self.assertRaises(KeyError):
                    dataset.attachment('S03', sid)

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
