import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pipeline
from operations import derive, distribution
from billing import Accounting


class OperationsTests(unittest.TestCase):
    def test_reported_bill_and_generation_timing_are_used_instead_of_price_estimate(self):
        row = {'arm': 'full', 'case_id': 'A', 'trial': 1, 'category': 'test', 'origin': 'authored',
               'gold': {'status': 'action'}, 'wall_ms': 500,
               'result': {'prediction': {'status': 'action', 'actions': [{}]},
                          'repairs': [{'attempted': True, 'outcome': 'validated', 'quote_diagnostics': [1]}]}}
        call = {'arm': 'full', 'case_id': 'A', 'trial': 1, 'call': 2, 'wall_ms': 300,
                'cost_usd': 99, 'is_validation_repair': True,
                'transport': {'response_json': {'usage': {'cost': .1}}}}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            (path/'generations.jsonl').write_text(json.dumps({'arm': 'full', 'case_id': 'A', 'trial': 1,
                'call': 2, 'data': {'total_cost': .2, 'latency': 250, 'generation_time': 200}})+'\n')
            op = derive(path, [row], [call], {'arms': []}, {'mode': 'live', 'complete': True})
            m = op['by_arm']['full']
            self.assertEqual(m['known_billed_cost_usd'], .2)
            self.assertEqual(m['known_estimated_cost_usd'], 99)
            self.assertEqual(m['known_repair_billed_cost_usd'], .2)
            self.assertEqual(m['openrouter_generation_time_ms']['mean'], 200)
            self.assertEqual(m['repair_validated_events'], 1)

    def test_missing_cost_and_incomplete_case_are_not_free_successes(self):
        row = {'arm': 'full_m01', 'case_id': 'A', 'trial': 1, 'category': 'authored', 'origin': 'authored',
               'gold': {'status': 'action'}, 'wall_ms': 200,
               'result': {'prediction': {'status': 'action', 'actions': [{}]}, 'quotes_exact': True}}
        call = {'arm': 'full_m01', 'case_id': 'A', 'trial': 1, 'call': 1, 'wall_ms': 100,
                'reply': {'input_tokens': 10, 'output_tokens': 20, 'model': 'test'}, 'cost_usd': .01}
        failed = {**call, 'call': 2, 'reply': None, 'cost_usd': None, 'error': 'timeout'}
        orphan = {**call, 'case_id': 'B'}
        config = {'phase': 'model_benchmark', 'arms': [{'id': 'full_m01'}, {'id': 'full_m02'}]}
        with tempfile.TemporaryDirectory() as d:
            op = derive(Path(d), [row], [call, failed, orphan], config, {'mode': 'live', 'complete': False})
            m = op['by_arm']['full_m01']
            self.assertAlmostEqual(m['known_estimated_cost_usd'], .02)
            self.assertFalse(m['cost_complete']); self.assertEqual(m['unknown_cost_calls'], 1)
            self.assertEqual(m['calls_without_completed_case'], 1)
            self.assertEqual(m['complete_case_cost_usd']['observations'], 0)
            self.assertFalse(op['cross_model_case_robustness'][0]['status_count_agreement'])
            self.assertTrue((Path(d)/'turn_metrics.csv').exists())

    def test_distribution_reports_observed_denominators_and_descriptive_p95(self):
        self.assertIsNone(distribution([])['p95'])
        self.assertEqual(distribution([100, None, 200])['observations'], 2)
        self.assertEqual(distribution([100, 200])['p95'], 195)


class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bundle = Path(os.getenv('ACTIONMAIL_EXPERIMENT_BUNDLE', str(ROOT.parent/'data/frozen-core')))
        if 'actionmail' not in sys.modules:
            pipeline.activate(bundle)
        else:
            assert Path(sys.modules['actionmail'].__file__).resolve().is_relative_to(bundle.resolve())
        import telemetry
        import engine
        from actionmail.reasoning import api_client
        cls.telemetry, cls.engine, cls.api = telemetry, engine, api_client

    def response(self, data):
        response = io.BytesIO(json.dumps(data).encode()); response.status = 200
        return response

    def test_observed_request_matches_frozen_contract_and_preserves_response_details(self):
        data = {'id': 'test-response', 'provider': 'authored-provider', 'model': 'resolved-test',
                'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'cost': .001,
                          'completion_tokens_details': {'reasoning_tokens': 3}}}
        client = self.telemetry.ObservedAPIClient('https://example.com/api', 'TEST_SECRET', 'test')
        frozen = self.api.APIClient('https://example.com/api', 'TEST_SECRET', 'test')
        with patch.object(self.telemetry, 'urlopen', return_value=self.response(data)) as observed:
            reply = client.complete('system', 'prompt')
            observed_payload = json.loads(observed.call_args.args[0].data)
        with patch.object(self.api, 'urlopen', return_value=self.response(data)) as original:
            expected = frozen.complete('system', 'prompt')
            self.assertEqual(observed_payload, json.loads(original.call_args.args[0].data))
        self.assertEqual((reply.content, reply.input_tokens, reply.output_tokens),
                         (expected.content, expected.input_tokens, expected.output_tokens))
        self.assertEqual(client.last_exchange['response_json'], data)
        self.assertNotIn('TEST_SECRET', json.dumps(client.last_exchange))
        self.assertIsNone(client.last_exchange['ttft_ms'])

    def test_no_text_failure_preserves_usage_finish_reason_and_call_lifecycle(self):
        data = {'choices': [{'message': {'content': None}, 'finish_reason': 'length'}],
                'usage': {'completion_tokens': 2048, 'cost': .01}}
        with tempfile.TemporaryDirectory() as d:
            client = self.telemetry.ObservedAPIClient('https://example.com/api', 'TEST_SECRET', 'test')
            meter = self.engine.Meter(1, Path(d)/'calls.jsonl')
            measured = meter.client(client, {'id': 'test', 'input_usd_per_million': 1,
                                            'output_usd_per_million': 1, 'request_usd': 0}, 5, 'full', 'A', 1)
            with patch.object(self.telemetry, 'urlopen', return_value=self.response(data)):
                with self.assertRaises(self.api.ModelCallError): measured.complete('system', 'prompt')
            trace = json.loads((Path(d)/'calls.jsonl').read_text())
            self.assertEqual(trace['transport']['response_json'], data)
            self.assertIsNone(trace['cost_usd']); self.assertIn('finish_reason=length', trace['error'])
            self.assertEqual(trace['turn_id'], 'full/A/trial-1/call-1')
            self.assertIn('call_started', (Path(d)/'events.jsonl').read_text())

    def test_quote_repair_turn_links_previous_reply_and_diagnostics(self):
        import copy
        bundle = Path(os.getenv('ACTIONMAIL_EXPERIMENT_BUNDLE', str(ROOT.parent/'data/frozen-core')))
        case = copy.deepcopy(pipeline.jsonl(ROOT/'tests/fixtures/smoke.jsonl')[1])
        good = case['scripted_responses'][0]
        bad = good.replace('Alex, please send the brief.', 'Alex, please send a brief.')
        with tempfile.TemporaryDirectory() as d:
            meter = self.engine.Meter(1, Path(d)/'calls.jsonl')
            model = meter.client(self.engine.Scripted([bad, good]),
                    {'id': 'test', 'input_usd_per_million': 1, 'output_usd_per_million': 1, 'request_usd': 0}, 5, 'full', 'A', 1)
            result = self.engine.execute('full', case, model)
            traces = pipeline.jsonl(Path(d)/'calls.jsonl')
            self.assertFalse(traces[0]['is_validation_repair']); self.assertTrue(traces[1]['is_validation_repair'])
            self.assertEqual(traces[1]['prior_turn_id'], traces[0]['turn_id'])
            self.assertEqual(traces[1]['repair_feedback']['previous_reply'], bad)
            self.assertTrue(traces[1]['repair_feedback']['quote_diagnostics'])
            self.assertEqual(result['repairs'][0]['outcome'], 'validated')

    def test_missing_actual_usage_baseline_stops_before_inference(self):
        bundle = Path(os.getenv('ACTIONMAIL_EXPERIMENT_BUNDLE', str(ROOT.parent/'data/frozen-core')))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'run'
            with patch.object(pipeline, 'activate'), patch.dict(os.environ, {'OPENROUTER_API_KEY': 'TEST_SECRET'}), \
                    patch.object(Accounting, 'snapshot', return_value={'key_usage_usd': None}), \
                    patch.object(self.telemetry.ObservedAPIClient, 'complete') as inference:
                with self.assertRaisesRegex(ValueError, 'baseline actual usage'):
                    pipeline.run(bundle, ROOT/'configs/stage1-model-benchmark-proposed.json', out, None, paid=True)
                inference.assert_not_called()
                self.assertFalse((out/'calls.jsonl').exists())
                self.assertFalse(pipeline.read(out/'run.json')['complete'])


class BillingTests(unittest.TestCase):
    def test_snapshot_filters_credentials_and_identity_fields(self):
        accountant = Accounting('TEST_SECRET', 'MANAGEMENT_SECRET')
        values = [{'available': True, 'data': {'usage': 1, 'label': 'TEST_SECRET', 'creator_user_id': 'private'}},
                  {'available': True, 'data': {'total_usage': 1, 'total_credits': 10}}]
        with patch.object(accountant, 'get', side_effect=values): snapshot = accountant.snapshot()
        self.assertEqual(snapshot['account_remaining_usd'], 9)
        self.assertNotIn('TEST_SECRET', json.dumps(snapshot)); self.assertNotIn('private', json.dumps(snapshot))

    def test_actual_counter_delta_reconciles_generation_bills_and_detects_topup(self):
        accountant = Accounting('TEST_SECRET')
        before = {'key_usage_usd': 1, 'account_usage_usd': 1, 'account_total_credits_usd': 10, 'account_remaining_usd': 9}
        after = {'key_usage_usd': 1.5, 'account_usage_usd': 1.5, 'account_total_credits_usd': 12, 'account_remaining_usd': 10.5}
        call = {'arm': 'full', 'case_id': 'A', 'trial': 1, 'call': 1,
                'transport': {'response_json': {'id': 'gen-test'}}}
        with tempfile.TemporaryDirectory() as d:
            with patch.object(accountant, 'snapshot', return_value=after), patch.object(accountant, 'generation', return_value={'available': True, 'data': {'total_cost': .5}}):
                audit = accountant.reconcile(Path(d), before, [call])
            self.assertEqual(audit['key_usage_delta_usd'], .5); self.assertEqual(audit['credits_added_usd'], 2)
            self.assertEqual(audit['account_balance_decrease_usd'], -1.5)
            self.assertTrue(audit['reconciled'])

    def test_delayed_bill_is_pending_and_shared_usage_gap_is_not_invented_cost(self):
        accountant = Accounting('TEST_SECRET')
        call = {'arm': 'full', 'case_id': 'A', 'trial': 1, 'call': 1, 'cost_usd': 999}
        with tempfile.TemporaryDirectory() as d:
            with patch.object(accountant, 'snapshot', return_value={'key_usage_usd': 2}), patch.object(accountant, 'generation', return_value={'available': False, 'error': 'http_404'}):
                audit = accountant.reconcile(Path(d), {'key_usage_usd': 1}, [call])
            self.assertFalse(audit['reconciled']); self.assertEqual(audit['missing_generation_cost_calls'], 1)
            self.assertEqual(audit['key_usage_delta_usd'], 1); self.assertEqual(audit['generation_cost_known_sum_usd'], 0)


if __name__ == '__main__': unittest.main()
