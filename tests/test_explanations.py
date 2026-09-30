import json
import unittest
from actionmail.domain.email import EmailPackage, ExternalSource
from actionmail.reasoning.model_client import ModelReply
from actionmail.reasoning.multi_response import parse_multi_response
from actionmail.workflow.multi_pipeline import process_email_multi
from actionmail.workflow.coverage import parse_plan


class ExplanationTests(unittest.TestCase):
    def email(self):
        return EmailPackage('test', 'alex@example.com', None, 'maya@example.com', ('alex@example.com',), 'Information', 'For your information only. No reply is required.')

    def result(self, quote):
        return {'status': 'no_action', 'actions': [], 'review_reason': None,
                'explanation': {'text': 'This is an informative message and explicitly requires no reply from Alex.',
                                'evidence': [{'source_id': 'body', 'quote': quote}]}}

    def test_no_action_explanation_survives_workflow_and_false_quote_is_rejected(self):
        class Model:
            def __init__(self, value): self.value = value
            def complete(self, system, user): return ModelReply(json.dumps(self.value), 'offline')
        run = process_email_multi(self.email(), Model(self.result('No reply is required.')))
        self.assertEqual(run.decision.status, 'no_action')
        self.assertEqual(run.decision.explanation.evidence[0].quote, 'No reply is required.')
        run = process_email_multi(self.email(), Model(self.result('Please reply immediately.')))
        self.assertEqual(run.decision.status, 'needs_review')
        self.assertTrue(run.validation_errors)
        self.assertFalse(run.decision.explanation.evidence)

    def test_missing_new_explanation_rejected_but_historical_reference_can_load(self):
        old = {'status': 'no_action', 'actions': [], 'review_reason': None}
        self.assertIsNone(parse_multi_response(json.dumps(old)).explanation)
        with self.assertRaisesRegex(ValueError, 'require an explanation'):
            parse_multi_response(json.dumps(old), require_explanation=True)
        value = self.result('No reply is required.')
        value['explanation']['evidence'] = []
        with self.assertRaisesRegex(ValueError, 'original evidence'):
            parse_multi_response(json.dumps(value), require_explanation=True)

    def test_skip_choice_cannot_quote_unread_document(self):
        inventory = (ExternalSource('attachment:1', 'attachment', 'balance.pdf'),)
        plan = {'sources': [{'source_id': 'attachment:1', 'relevance': 'irrelevant', 'reason': 'Informative only.',
                            'evidence': [{'source_id': 'attachment:1', 'quote': 'No tasks here.'}]}]}
        with self.assertRaisesRegex(ValueError, 'not supplied'):
            parse_plan(json.dumps(plan), inventory, sources={'body': self.email().body})
        plan['sources'][0]['evidence'] = [{'source_id': 'body', 'quote': 'For your information only.'}]
        self.assertEqual(parse_plan(json.dumps(plan), inventory, sources={'body': self.email().body})[0].evidence[0].source_id, 'body')
