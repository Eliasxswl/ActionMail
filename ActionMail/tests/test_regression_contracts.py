import json
import unittest
from unittest.mock import patch
from actionmail.domain.email import EmailPackage, SourceText
from actionmail.evaluation.cli import PROJECT_ROOT, DEFAULT_MAILEX_ROOT
from actionmail.evaluation.suite import load_suite
from actionmail.reasoning.multi_response import parse_multi_response
from actionmail.reasoning.api_client import APIClient, MAX_OUTPUT_TOKENS
from actionmail.workflow.context import decision_prompt
from actionmail.workflow.multi_pipeline import _validate


class RegressionContractTests(unittest.TestCase):
    def test_supplied_header_quote_has_its_own_source_and_body_cannot_impersonate_it(self):
        thread = SourceText('thread:1', 'Sara, please review it.', sender='Maureen', recipients='Shackleton, Sara')
        email = EmailPackage('test', 'marie@example.com', None, 'sender@example.com', ('marie@example.com',), 'Follow up', '', thread=(thread,))
        value = {'status': 'needs_review', 'actions': [], 'reason': 'The older request was addressed to Sara.',
                 'evidence': [{'source_id': 'thread:1', 'quote': 'To: Shackleton, Sara'}]}
        result, errors = _validate(email, parse_multi_response(json.dumps(value), require_explanation=True), 3)
        self.assertFalse(errors)
        self.assertEqual(result.evidence[0].source_id, 'thread:1:headers')
        self.assertIn('SOURCE thread:1:headers', decision_prompt(email))
        self.assertEqual(email.sources()['thread:1'], thread.text)
        value['evidence'][0]['quote'] = 'To: marie@example.com'
        _, errors = _validate(email, parse_multi_response(json.dumps(value), require_explanation=True), 3)
        self.assertTrue(errors)

    def test_saved_c12_reply_revalidates_but_changed_s02_amount_is_still_rejected(self):
        cases = {c.case_id: c for c in load_suite(PROJECT_ROOT / 'evaluation/active_suite.json', DEFAULT_MAILEX_ROOT)}
        path = PROJECT_ROOT / 'tests/fixtures/regression_replies.json'
        rows = json.loads(path.read_text(encoding='utf-8'))['regression']['rows']
        decision = parse_multi_response(rows['C12']['raw_model_response'], require_explanation=True)
        aligned, errors = _validate(cases['C12'].email, decision, 3)
        self.assertFalse(errors)
        self.assertEqual(aligned.status, 'needs_review')
        self.assertIn('thread:1:headers', {e.source_id for e in aligned.evidence})
        decision = parse_multi_response(rows['S02']['raw_model_response'], require_explanation=True)
        _, errors = _validate(cases['S02'].email, decision, 3)
        self.assertTrue(errors)

    def test_api_request_and_preflight_share_larger_output_budget(self):
        from actionmail.evaluation.preflight import MAX_OUTPUT_TOKENS as estimate_cap
        self.assertEqual(estimate_cap, MAX_OUTPUT_TOKENS)
        self.assertGreater(MAX_OUTPUT_TOKENS, 800)
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps({'choices': [{'message': {'content': '{}'}}]}).encode()
        with patch('actionmail.reasoning.api_client.urlopen', return_value=Response()) as transport:
            APIClient('http://127.0.0.1/test', 'offline-test-key', 'offline').complete('system', 'user')
        payload = json.loads(transport.call_args.args[0].data)
        self.assertEqual(payload['max_tokens'], MAX_OUTPUT_TOKENS)
