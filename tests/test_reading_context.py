import json
import unittest
from dataclasses import replace
from actionmail.domain.email import EmailPackage, ExternalSource, SourceText
from actionmail.evaluation.cli import PROJECT_ROOT, DEFAULT_MAILEX_ROOT
from actionmail.evaluation.suite import load_suite
from actionmail.reasoning.model_client import ModelReply
from actionmail.workflow.coverage import WorkflowLimits
from actionmail.workflow.multi_pipeline import process_email_multi_with_external


class ScriptedModel:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def complete(self, system, user):
        self.calls.append((system, user))
        return ModelReply(json.dumps(next(self.replies)), 'offline')


def result(status, body, reason):
    return {'status': status, 'actions': [], 'reason': reason, 'evidence': [{'source_id': 'body', 'quote': body}]}


class ReadingContextTests(unittest.TestCase):
    def email(self, body, source):
        return EmailPackage('test', 'alex@example.com', None, 'maya@example.com', ('alex@example.com',), 'Update', body,
                            external_sources=(source,))

    def plan(self, body, relevance):
        return {'sources': [{'source_id': 'link:1', 'relevance': relevance, 'reason': 'Primary content' if relevance == 'decisive' else 'Generic footer',
                             'evidence': [{'source_id': 'body', 'quote': body}]}]}

    def test_primary_project_link_is_read_before_decision_without_extra_calls(self):
        body = 'Project details are posted at https://example.org/update'
        source = ExternalSource('link:1', 'link', 'https://example.org/update', snapshot_text='Maya will prepare the report. This page is informational for Alex.')
        decision = result('no_action', body, 'The supplied page assigns work to Maya, not Alex.')
        decision['evidence'] = [{'source_id': 'link:1', 'quote': source.snapshot_text}]
        model = ScriptedModel([self.plan(body, 'decisive'), decision])
        run = process_email_multi_with_external(self.email(body, source), model)
        self.assertEqual(run.decision.status, 'no_action')
        self.assertEqual(len(model.calls), 2)
        self.assertNotIn(source.snapshot_text, model.calls[0][1])
        self.assertIn(source.snapshot_text, model.calls[1][1])
        self.assertIn('"state": "read"', model.calls[1][1])
        self.assertEqual(run.read_records[0].source_id, 'link:1')

    def test_skipped_footer_reason_reaches_decision_without_polluting_context(self):
        body = 'For your information only. No response needed. Company website: https://example.org'
        source = ExternalSource('link:1', 'link', 'https://example.org', snapshot_text='UNRELATED PAYROLL DATA DO NOT INCLUDE')
        model = ScriptedModel([self.plan(body, 'irrelevant'), result('no_action', body, 'Informational email; the generic website was deliberately skipped.')])
        run = process_email_multi_with_external(self.email(body, source), model)
        self.assertEqual(run.decision.status, 'no_action')
        self.assertFalse(run.read_records)
        self.assertIn('skipped_as_irrelevant', model.calls[1][1])
        self.assertIn('Generic footer', model.calls[1][1])
        self.assertNotIn(source.snapshot_text, model.calls[1][1])

    def test_unavailable_primary_link_requires_review_before_final_extraction(self):
        body = 'Project details are posted at https://example.org/update'
        source = ExternalSource('link:1', 'link', 'https://example.org/update')
        model = ScriptedModel([self.plan(body, 'decisive')])
        run = process_email_multi_with_external(self.email(body, source), model)
        self.assertEqual(run.decision.status, 'needs_review')
        self.assertEqual(len(model.calls), 1)
        self.assertTrue(run.read_failures)
        self.assertEqual(run.decision.evidence[0].quote, body)

    def test_c13_missing_inventory_and_original_thread_ownership_are_explicit(self):
        c13 = next(c for c in load_suite(PROJECT_ROOT / 'evaluation/active_suite.json', DEFAULT_MAILEX_ROOT) if c.case_id == 'C13')
        model = ScriptedModel([result('needs_review', 'Please review this material and provide me with any material comments that you may have.', 'The material needed for the newest review request was not supplied.')])
        run = process_email_multi_with_external(c13.email, model)
        self.assertEqual(run.decision.status, 'needs_review')
        self.assertEqual(len(model.calls), 1)
        system, prompt = model.calls[0]
        self.assertIn('EXTERNAL AVAILABILITY', prompt)
        self.assertIn('[]', prompt)
        self.assertIn('not that the email cannot refer to missing material', prompt)
        for thread in c13.email.thread:
            self.assertIn(thread.recipients, prompt)
        self.assertIn('older tasks belong only to their actual addressees', system.lower())

    def test_reading_states_survive_segment_and_merge_paths(self):
        body = 'FYI only. Visit https://example.org for company background.'
        source = ExternalSource('link:1', 'link', 'https://example.org', snapshot_text='PRIVATE IRRELEVANT CONTENT')
        email = replace(self.email(body, source), thread=(SourceText('thread:1', 'x' * 240),))
        limits = WorkflowLimits(segment_chars=120, overlap_chars=0)
        # Three planning windows, four extraction windows (subject/body/two thread), one merge.
        plans = [self.plan(body, 'irrelevant') for _ in range(3)]
        decisions = [result('no_action', body, 'No request in this message.') for _ in range(4)]
        for i in (2, 3):
            decisions[i]['evidence'] = [{'source_id': 'thread:1', 'quote': 'x' * 120}]
        model = ScriptedModel([*plans, *decisions, result('no_action', body, 'No current task; background website skipped.')])
        run = process_email_multi_with_external(email, model, limits=limits)
        self.assertEqual(run.decision.status, 'no_action', run.validation_errors)
        for _, prompt in model.calls[3:]:
            self.assertIn('skipped_as_irrelevant', prompt)
            self.assertNotIn(source.snapshot_text, prompt)


if __name__ == '__main__':
    unittest.main()
