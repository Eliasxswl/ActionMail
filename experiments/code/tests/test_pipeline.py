import copy
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pipeline
import scoring
import design

BUNDLE = Path(os.getenv('ACTIONMAIL_EXPERIMENT_BUNDLE', str(ROOT.parent / 'data/frozen-core')))


class PurePipelineTests(unittest.TestCase):
    def test_matrix_selectors_are_input_based_and_trials_explicit(self):
        config = pipeline.read(ROOT / 'configs/core.json')
        cases = [{'case_id': 'N01', 'email': {'thread': [], 'external_sources': []}},
                 {'case_id': 'A23', 'email': {'thread': [1], 'external_sources': [1]}}]
        queue = list(pipeline.tasks(config, cases, ['no_thread', 'no_external', 'stability']))
        self.assertEqual(sum(a['id'] == 'no_thread' for a, _, _ in queue), 1)
        self.assertEqual(sum(a['id'] == 'no_external' for a, _, _ in queue), 1)
        self.assertEqual(sum(a['id'] == 'stability' for a, _, _ in queue), 6)
        with self.assertRaises(ValueError):
            list(pipeline.tasks(config, cases, ['typo']))

    def test_reviews_count_as_missed_actions_and_alternatives_stay_separate(self):
        def row(cid, gold, pred, alternatives=[]):
            return {'case_id': cid, 'gold': {'status': gold}, 'accepted_outcomes': alternatives,
                    'result': {'prediction': {'status': pred, 'actions': [1] if pred == 'action' else []}}, 'wall_ms': 1}
        result = scoring.metrics([row('a', 'action', 'needs_review'),
                                  row('b', 'needs_review', 'action', [{'status': 'action', 'action_count': 1}])])
        self.assertEqual(result['action_fn'], 1)
        self.assertEqual(result['action_fp'], 1)
        self.assertEqual(result['strict_status_match'], 0)
        self.assertEqual(result['accepted_joint_status_count_match'], 1)

    def test_zero_denominator_is_unknown_not_perfect(self):
        result = scoring.metrics([])
        self.assertIsNone(result['action_precision'])
        self.assertIsNone(result['review_recall'])

    def test_scalar_deadlines_distinguish_nulls_from_dates(self):
        rows = []
        for deadline in [None, '2026-10-02']:
            rows.append({'gold': {'status': 'action', 'deadline': deadline}, 'accepted_outcomes': [],
                         'result': {'prediction': {'status': 'action', 'actions': [{'deadline': deadline}]}}, 'wall_ms': 1})
        self.assertEqual(scoring.metrics(rows)['deadlines'],
                         {'non_null_checked': 1, 'non_null_match': 1, 'null_checked': 1, 'null_match': 1})

    def test_comparator_is_sliced_to_identical_cases_and_incomplete_trials_are_not_stable(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            pipeline.dump(out/'run.json', {'mode': 'scripted engineering', 'complete': False,
                          'planned_analyses': 6, 'paid_calls': 0, 'measured_usd': 0, 'reserved_usd': 0})
            pipeline.dump(out/'config.json', {'arms': [{'id': 'full', 'trials': 1},
                           {'id': 'ablation', 'trials': 1, 'comparator': 'full'}, {'id': 'stability', 'trials': 3}]})
            def row(arm, cid, predicted):
                return {'arm': arm, 'case_id': cid, 'trial': 1, 'category': 'sample', 'origin': 'authored',
                        'gold': {'status': 'no_action'}, 'accepted_outcomes': [], 'wall_ms': 1,
                        'result': {'prediction': {'status': predicted, 'actions': []}}}
            rows = [row('full', 'A', 'no_action'), row('full', 'B', 'needs_review'),
                    row('ablation', 'A', 'no_action'), row('stability', 'A', 'no_action')]
            (out/'rows.jsonl').write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf-8')
            scoring.score_run(out); summary = pipeline.read(out/'summary.json')
            pair = summary['paired_comparisons']['ablation']
            self.assertEqual(pair['paired_analyses'], 1)
            self.assertEqual(pair['comparator_metrics']['strict_status_rate'], 1)
            self.assertEqual(summary['arms']['full']['strict_status_rate'], 0.5)
            self.assertFalse(summary['repeatability'][0]['stable_status_count'])


class TwoStageDesignTests(unittest.TestCase):
    def config(self):
        catalog = {'source': 'public-test-catalog', 'retrieved_utc': 'authored-test-time',
                   'models': [{'id': mid, 'pricing': {'prompt': '0.0000001', 'completion': '0.0000005'}}
                              for _, mid, _, _ in design.CANDIDATES]}
        return design.stage1_config(catalog)

    def test_stage_one_has_all_candidate_full_arms_and_interleaves_by_case(self):
        config = self.config()
        cases = [{'case_id': 'A', 'email': {}}, {'case_id': 'B', 'email': {}}]
        queue = pipeline.scheduled_tasks(config, cases)
        count = len(design.CANDIDATES)
        self.assertEqual(len(queue), 2 * count)
        self.assertEqual([c['case_id'] for _, c, _ in queue], ['A']*count + ['B']*count)
        self.assertTrue(all(a['mode'] == 'full' for a, _, _ in queue))
        self.assertEqual(len({m['family'] for m in config['models'].values()}), 4)

    def fake_completed_benchmark(self, out, complete=True):
        config = self.config(); pipeline.dump(out/'config.json', config)
        pipeline.dump(out/'run.json', {'complete': complete, 'bundle_sha256': 'frozen-test-bundle'})
        metric = {'analyses': 60, 'action_precision': 1, 'action_recall': 1, 'model_errors': 0, 'quote_exact_cases': 60}
        pipeline.dump(out/'summary.json', {'arms': {a['id']: metric for a in config['arms']},
                      'cost_by_arm': {a['id']: {'reported_usage_estimate_usd': 0, 'calls': 0} for a in config['arms']}})

    def test_stage_two_requires_finished_benchmark_and_two_or_three_distinct_models(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d); self.fake_completed_benchmark(out, False)
            with self.assertRaises(ValueError): design.stage2_config(out, ['m01','m02'], 'Test reason')
            self.fake_completed_benchmark(out, True)
            with self.assertRaises(ValueError): design.stage2_config(out, ['m01'], 'Test reason')
            with self.assertRaises(ValueError): design.stage2_config(out, ['m01','m01'], 'Test reason')
            with self.assertRaises(ValueError): design.stage2_config(out, ['m01','unknown'], 'Test reason')

    def test_stage_two_uses_same_arms_and_own_fresh_comparator_for_each_selected_model(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d); self.fake_completed_benchmark(out)
            config = design.stage2_config(out, ['m01','m03','m06'], 'Quality, cost and family contrast, synthetic test')
            self.assertEqual(len(config['arms']), 21)
            self.assertEqual(config['required_bundle_sha256'], 'frozen-test-bundle')
            self.assertFalse(config['selection']['semantic_review_complete_at_selection'])
            for arm in config['arms']:
                if arm['layer'] in ['ablation', 'baseline']:
                    self.assertEqual(arm['comparator'], 'full_'+arm['model'])
            self.assertEqual(len({a['id'] for a in config['arms']}), 21)

    def test_incomplete_semantic_review_never_becomes_a_semantic_performance_claim(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d); self.fake_completed_benchmark(out)
            packet=design.screening(out)
            self.assertFalse(packet['semantic_review_complete'])
            self.assertTrue(all(c['semantic'] is None for c in packet['candidates']))
            self.assertEqual(packet['phase'], 'screening, not final model ranking')


@unittest.skipUnless((BUNDLE / 'manifest.json').exists(), 'Prepare a frozen bundle before core adapter tests')
class FrozenCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pipeline.verify_bundle(BUNDLE)
        if 'actionmail' not in sys.modules:
            pipeline.activate(BUNDLE)
        else:
            assert Path(sys.modules['actionmail'].__file__).resolve().is_relative_to(BUNDLE.resolve())
        import engine
        cls.engine = engine
        cls.case = pipeline.jsonl(ROOT / 'tests/fixtures/smoke.jsonl')[1]

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'pipeline.py'), *map(str, args)],
                              capture_output=True, text=True, encoding='utf-8',
                              env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})

    def test_tampered_runtime_and_extra_modules_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'bundle'
            shutil.copytree(BUNDLE, target, ignore=shutil.ignore_patterns('__pycache__'))
            module = target / 'runtime/actionmail/domain/decision.py'
            module.write_text(module.read_text(encoding='utf-8') + '\n# changed\n', encoding='utf-8')
            with self.assertRaises(ValueError): pipeline.verify_bundle(target)
            module.write_bytes((BUNDLE / 'runtime/actionmail/domain/decision.py').read_bytes())
            (target / 'runtime/actionmail/unexpected.py').write_text('x=1')
            with self.assertRaises(ValueError): pipeline.verify_bundle(target)

    def test_live_calls_require_approval_and_verified_prices_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'run'
            denied = self.cli('run', '--bundle', BUNDLE, '--arm', 'full', '--output', out)
            self.assertNotEqual(denied.returncode, 0); self.assertFalse(out.exists())
            no_prices = self.cli('run', '--bundle', BUNDLE, '--arm', 'full', '--approve-paid', '--output', out)
            self.assertNotEqual(no_prices.returncode, 0); self.assertFalse(out.exists())

    def test_scripted_cannot_impersonate_corpus_inference(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.cli('run', '--bundle', BUNDLE, '--arm', 'full', '--scripted', '--output', Path(d)/'run')
            self.assertNotEqual(result.returncode, 0)

    def test_existing_outputs_are_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'run'; out.mkdir(); (out / 'marker').write_text('keep')
            result = self.cli('run', '--bundle', BUNDLE, '--arm', 'rules', '--output', out)
            self.assertNotEqual(result.returncode, 0); self.assertEqual((out/'marker').read_text(), 'keep')

    def test_no_repair_disables_retry_but_keeps_rejection(self):
        case = copy.deepcopy(self.case)
        good = case['scripted_responses'][0]
        bad = good.replace('Alex, please send the brief.', 'Invented request.')
        full = self.engine.Scripted([bad, good])
        disabled = self.engine.Scripted([bad, good])
        self.assertEqual(self.engine.execute('full', case, full)['prediction']['status'], 'action')
        self.assertEqual(self.engine.execute('no_repair', case, disabled)['prediction']['status'], 'needs_review')
        self.assertEqual(full.calls, 2); self.assertEqual(disabled.calls, 1)

    def test_read_all_and_selective_reach_same_source_with_different_planning(self):
        case = copy.deepcopy(self.case)
        case['email']['body'] = 'Alex, do the task in the attachment.'
        case['email']['external_sources'] = [{'source_id': 'attachment:1', 'kind': 'attachment', 'name': 'brief.txt',
             'snapshot_text': 'Send the brief by 2026-10-03.', 'content': None, 'media_type': 'text/plain', 'charset': None}]
        plan = json.dumps({'sources': [{'source_id': 'attachment:1', 'relevance': 'decisive', 'reason': 'Task dependency',
                          'evidence': [{'source_id': 'body', 'quote': case['email']['body']}]}]})
        reply = json.dumps({'status': 'action', 'actions': [{'kind': 'perform_task', 'text': 'Send the brief.',
                'deadline': '2026-10-03', 'evidence': [{'source_id': 'attachment:1', 'quote': 'Send the brief by 2026-10-03.'}]}],
                'reason': 'The attachment supplies the task.', 'evidence': [{'source_id': 'body', 'quote': case['email']['body']}]})
        selective = self.engine.Scripted([plan, reply]); all_sources = self.engine.Scripted([reply])
        a = self.engine.execute('full', case, selective); b = self.engine.execute('read_all', case, all_sources)
        self.assertEqual(a['prediction'], b['prediction']); self.assertTrue(a['quotes_exact'] and b['quotes_exact'])
        self.assertEqual(len(a['reads']), 1); self.assertEqual(selective.calls, 2); self.assertEqual(all_sources.calls, 1)

    def test_budget_stops_before_request_and_failure_retains_reservation(self):
        prices = {'id': 'test', 'input_usd_per_million': 1, 'output_usd_per_million': 1, 'request_usd': 0}
        with tempfile.TemporaryDirectory() as d:
            fake = self.engine.Scripted(['{}']); meter = self.engine.Meter(0.000001, Path(d)/'calls')
            client = meter.client(fake, prices, 5, 'full', 'A', 1)
            with self.assertRaises(self.engine.BudgetStop): client.complete('system', 'input')
            self.assertEqual(fake.calls, 0)
            failure = self.engine.Scripted([]); meter = self.engine.Meter(1, Path(d)/'failures')
            client = meter.client(failure, prices, 1, 'full', 'A', 1)
            with self.assertRaises(self.engine.ModelCallError): client.complete('system', 'input')
            self.assertGreater(meter.reserved, 0); self.assertEqual(meter.unknown_usage_calls, 1)
            with self.assertRaises(self.engine.BudgetStop): client.complete('system', 'input')

    def test_thread_removal_preserves_latest_message_and_source_checks(self):
        case = copy.deepcopy(self.case)
        case['email']['thread'] = [{'source_id': 'thread:1', 'text': 'Alex, please send the old brief.',
                                    'sender': 'old@example.com', 'recipients': 'alex@example.com', 'cc': '', 'subject': 'Old request'}]
        original = json.dumps(case, sort_keys=True)
        reply = case['scripted_responses'][0]
        result = self.engine.execute('no_thread', case, self.engine.Scripted([reply]))
        self.assertEqual(result['prediction']['status'], 'action')
        self.assertNotIn('thread:1', {x['source_id'] for x in result['coverage']})
        self.assertEqual(json.dumps(case, sort_keys=True), original)

    def test_no_external_retains_missing_dependency_without_reading(self):
        case = copy.deepcopy(self.case)
        case['email']['body'] = 'Alex, do the task in the attachment.'
        case['email']['external_sources'] = [{'source_id': 'attachment:1', 'kind': 'attachment', 'name': 'brief.txt',
             'snapshot_text': 'Send the brief.', 'content': None, 'media_type': 'text/plain', 'charset': None}]
        reply = json.dumps({'status': 'needs_review', 'actions': [], 'reason': 'Decisive attachment was not supplied.',
                            'evidence': [{'source_id': 'body', 'quote': case['email']['body']}]})
        result = self.engine.execute('no_external', case, self.engine.Scripted([reply]))
        self.assertEqual(result['prediction']['status'], 'needs_review')
        self.assertEqual(result['reads'], [])
        self.assertTrue(result['quotes_exact'])

    def test_rescoring_preserves_human_edits_and_rejects_gold_mutation(self):
        smoke_fixture = ROOT / 'tests/fixtures/smoke.jsonl'
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'run'
            smoke = Path(d) / 'smoke'
            shutil.copytree(BUNDLE, smoke, ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copyfile(smoke_fixture, smoke / 'dataset.jsonl')
            pipeline.dump(smoke / 'manifest.json', {'format': 1,
                'files': {k:v for k,v in pipeline.file_hashes(smoke).items() if k!='manifest.json'},
                'case_count': 3, 'dataset_role': 'scripted engineering smoke; not model evaluation'})
            result = self.cli('run', '--bundle', smoke, '--arm', 'full', '--scripted', '--output', out)
            self.assertEqual(result.returncode, 0, result.stderr)
            sheet = out/'semantic_review.csv'; original = sheet.read_bytes()
            scoring.score_run(out); self.assertEqual(sheet.read_bytes(), original)
            scoring.score_review(out)
            self.assertFalse(pipeline.read(out/'semantic_summary.json')['complete'])
            with sheet.open(encoding='utf-8-sig', newline='') as f:
                entries = list(csv.DictReader(f)); fields = entries[0].keys()
            entries[0]['gold'] = '{}'
            with sheet.open('w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fields); writer.writeheader(); writer.writerows(entries)
            with self.assertRaises(ValueError): scoring.score_review(out)


if __name__ == '__main__': unittest.main()
