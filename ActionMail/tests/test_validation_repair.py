import json
import unittest
from dataclasses import replace
from types import SimpleNamespace
from actionmail.domain.email import EmailPackage, ExternalSource
from actionmail.evaluation.cli import PROJECT_ROOT, DEFAULT_MAILEX_ROOT, _run_one
from actionmail.evaluation.metrics import summarize_v2
from actionmail.evaluation.suite import load_suite
from actionmail.guardrails.matching import diagnose_quotes
from actionmail.reasoning.model_client import ModelReply
from actionmail.reasoning.api_client import ModelCallError
from actionmail.workflow.multi_pipeline import process_email_multi, process_email_multi_with_external
from actionmail.workflow.repair import RepairSession


class Model:
    def __init__(self, values): self.values, self.calls = iter(values), []
    def complete(self, system, prompt):
        self.calls.append(prompt)
        value = next(self.values)
        if isinstance(value, Exception): raise value
        return ModelReply(value if isinstance(value, str) else json.dumps(value), 'offline', 10, 5, 1)


class RepairTests(unittest.TestCase):
    def email(self):
        return EmailPackage('test', 'alex@example.com', None, 'maya@example.com', ('alex@example.com',), 'FYI', 'No response required. The balance is $25k-$50k.')
    def value(self, quote):
        return {'status': 'no_action', 'actions': [], 'reason': 'Informative only.', 'evidence': [{'source_id': 'body', 'quote': quote}]}

    def test_evaluation_saves_both_replies_and_counts_both_calls_and_cost(self):
        case = SimpleNamespace(case_id='offline', email=self.email(), source_hash='offline',
                               gold={'status': 'no_action', 'actions': []},
                               record={'category': 'informative', 'source': {'kind': 'fixture'}})
        model = Model([self.value('The balance is $25k-$50.'), self.value('The balance is $25k-$50k.')])
        row = _run_one(case, 'llm', model, (1., 2., .01), schema='v2', score_frozen=True)
        self.assertEqual(row['model_calls'], 2)
        self.assertEqual(len(row['raw_model_responses']), 2)
        self.assertEqual(row['usage']['input_tokens'], 20)
        self.assertEqual(row['usage']['output_tokens'], 10)
        self.assertAlmostEqual(row['estimated_cost_usd'], .02004)
        counts = summarize_v2([row], 1)['counts']
        self.assertEqual(counts['validation_repairs'], 1)
        self.assertEqual(counts['validated_repairs'], 1)

    def test_high_similarity_amount_error_is_not_accepted_and_valid_correction_is_saved(self):
        bad, good = self.value('The balance is $25k-$50.'), self.value('The balance is $25k-$50k.')
        diagnostic = diagnose_quotes(json.dumps(bad), {'body': self.email().body})[0]['candidates'][0]
        self.assertTrue(diagnostic['high_similarity'])
        self.assertTrue(diagnostic['critical_difference'])
        self.assertFalse(diagnostic['auto_accepted'])
        model = Model([bad, good])
        run = process_email_multi(self.email(), model)
        self.assertEqual(run.decision.status, 'no_action')
        self.assertFalse(run.validation_errors)
        self.assertEqual(len(run.replies), 2)
        self.assertEqual(json.loads(run.replies[0].content), bad)
        self.assertEqual(run.repair_attempts[0]['outcome'], 'validated')
        self.assertIn('The balance is $25k-$50k.', model.calls[1])

    def test_second_invalid_reply_stops_and_api_failure_is_not_retried(self):
        bad = self.value('The balance is $25k-$50.')
        model = Model([bad, bad])
        run = process_email_multi(self.email(), model)
        self.assertEqual(len(model.calls), 2)
        self.assertEqual(run.decision.status, 'needs_review')
        self.assertTrue(run.validation_errors)
        self.assertEqual(run.repair_attempts[0]['outcome'], 'validation_failure')
        model = Model([ModelCallError('offline network failure')])
        run = process_email_multi(self.email(), model)
        self.assertEqual(len(model.calls), 1)
        self.assertFalse(run.repair_attempts)
        self.assertEqual(run.failed_model_calls, 1)

    def test_schema_repair_and_valid_review_do_not_share_failure_semantics(self):
        model = Model(['not json', self.value('No response required.')])
        run = process_email_multi(self.email(), model)
        self.assertEqual(run.decision.status, 'no_action')
        self.assertEqual(len(model.calls), 2)
        review = {'status': 'needs_review', 'actions': [], 'reason': 'Necessary material is unavailable.', 'evidence': [{'source_id': 'body', 'quote': 'No response required.'}]}
        model = Model([review])
        run = process_email_multi(self.email(), model)
        self.assertEqual(len(model.calls), 1)
        self.assertFalse(run.repair_attempts)

    def test_retry_allowance_is_shared_between_planning_and_extraction(self):
        email = replace(self.email(), external_sources=(ExternalSource('link:1', 'link', 'https://example.org', snapshot_text='Unrelated content'),))
        plan = {'sources': [{'source_id': 'link:1', 'relevance': 'irrelevant', 'reason': 'Background.', 'evidence': [{'source_id': 'body', 'quote': 'No response required.'}]}]}
        model = Model(['invalid plan', plan, self.value('The balance is $25k-$50.')])
        run = process_email_multi_with_external(email, model)
        self.assertEqual(len(model.calls), 3)
        self.assertEqual(run.decision.status, 'needs_review')
        self.assertEqual(sum(e['attempted'] for e in run.repair_attempts), 1)
        self.assertEqual(run.repair_attempts[-1]['outcome'], 'skipped_retry_budget')
        self.assertFalse(run.read_records)
        self.assertNotIn('Unrelated content', model.calls[-1])

    def test_feedback_respects_prompt_budget(self):
        model = Model(['bad json'])
        session, replies = RepairSession(), []
        with self.assertRaises(ValueError):
            session.call(model, 'system', 'prompt', json.loads, {'body': 'test'}, replies, stage='test', limit=10)
        self.assertEqual(len(model.calls), 1)
        self.assertFalse(session.used)
        self.assertEqual(session.events[0]['outcome'], 'skipped_prompt_budget')

    def test_negation_and_repeated_candidates_are_flagged(self):
        value = self.value('Please approve the invoice today.')
        source = 'Please do not approve the invoice today.'
        diagnostic = diagnose_quotes(json.dumps(value), {'body': source})[0]['candidates'][0]
        self.assertTrue(diagnostic['critical_difference'])
        value = self.value('The balance is $25k-$50.')
        source = 'The balance is $25k-$50k.\nThe balance is $25k-$50k.'
        diagnostic = diagnose_quotes(json.dumps(value), {'body': source})[0]['candidates'][0]
        self.assertFalse(diagnostic['unique_in_source'])

    def test_saved_s02_can_be_corrected_without_altering_historical_reply(self):
        path = PROJECT_ROOT / 'tests/fixtures/regression_replies.json'
        row = json.loads(path.read_text(encoding='utf-8'))['contract']['rows']['S02']
        case = next(c for c in load_suite(PROJECT_ROOT / 'evaluation/active_suite.json', DEFAULT_MAILEX_ROOT) if c.case_id == 'S02')
        fixed = json.loads(row['raw_model_response'])
        fixed['evidence'][0]['quote'] = case.email.body.split('\n- Beau')[0]
        model = Model([row['raw_model_response'], fixed])
        run = process_email_multi(case.email, model)
        self.assertEqual(run.decision.status, 'no_action')
        self.assertEqual(run.replies[0].content, row['raw_model_response'])
        self.assertTrue(run.repair_attempts[0]['quote_diagnostics'][0]['candidates'][0]['critical_difference'])
        self.assertFalse(run.validation_errors)
