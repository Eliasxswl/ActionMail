"""Offline acceptance of short commands, saved-run selection and consent gates."""
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from actionmail import cli


class ShortCommandTests(unittest.TestCase):
    def call(self, arguments):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            try:
                code = cli.main(arguments)
            except SystemExit as exc:
                code = exc.code
        return code, output.getvalue(), error.getvalue()

    def save_run(self, root, name, started, complete=True):
        path = root / name
        path.mkdir()
        (path / 'run.json').write_text(json.dumps({'started_at_utc': started, 'schema': 'v2'}), encoding='utf-8')
        (path / 'summary.json').write_text(json.dumps({'complete': complete}), encoding='utf-8')
        (path / 'cases.jsonl').write_text(json.dumps({'case_id': 'S02', 'prediction': {'status': 'action'},
                                                    'raw_model_responses': ['raw trace'], 'repair_attempts': ['repair']}) + '\n', encoding='utf-8')

    def test_demo_respects_equals_output_path_and_refuses_overwrite(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'chosen'
            code, output, _ = self.call(['demo', f'--output-dir={path}'])
            self.assertEqual(code, 0)
            result = json.loads(output)['result']
            self.assertEqual(result['real_model_calls'], 0)
            self.assertEqual(result['real_provider_requests'], 0)
            self.assertEqual(result['simulated_events'], 1)
            original = (path / 'records.json').read_bytes()
            self.assertEqual(self.call(['demo', f'--output-dir={path}'])[0], 1)
            self.assertEqual((path / 'records.json').read_bytes(), original)

    def test_default_demo_creates_distinct_private_outputs(self):
        with TemporaryDirectory() as temp, patch.object(cli, 'PROJECT_ROOT', Path(temp)):
            for _ in range(2):
                self.assertEqual(self.call(['demo'])[0], 0)
            folders = list((Path(temp) / 'results' / 'private').iterdir())
            self.assertEqual(len(folders), 2)
            self.assertTrue(all((folder / 'summary.json').is_file() for folder in folders))

    def test_latest_complete_case_and_trace_selection(self):
        with TemporaryDirectory() as temp, patch.object(cli, 'EVALUATIONS', Path(temp)):
            root = Path(temp)
            self.save_run(root, 'old', '2026-10-01')
            self.save_run(root, 'latest', '2026-10-02')
            self.save_run(root, 'partial', '2026-10-03', False)
            code, output, _ = self.call(['results', '--case', 'S02'])
            value = json.loads(output)
            self.assertEqual(code, 0)
            self.assertEqual(value['run'], 'latest')
            self.assertNotIn('raw_model_responses', value['case'])
            self.assertNotIn('repair_attempts', value['case'])
            value = json.loads(self.call(['results', '--case', 'S02', '--trace'])[1])
            self.assertEqual(value['case']['raw_model_responses'], ['raw trace'])
            self.assertEqual(len(json.loads(self.call(['results', '--all', '--json'])[1])), 3)
            value = json.loads(self.call(['results', '--run', 'partial', '--case', 'S02'])[1])
            self.assertEqual(value['run'], 'partial')
            self.assertEqual(self.call(['results', '--run', 'missing'])[0], 1)
            self.assertEqual(self.call(['results', '--all', '--case', 'S02'])[0], 2)
            self.assertEqual(self.call(['results', '--trace'])[0], 2)

    def test_saved_alias_does_not_load_corpus_or_infer(self):
        with TemporaryDirectory() as temp, patch.object(cli, 'EVALUATIONS', Path(temp)), \
                patch('actionmail.evaluation.cli.load_suite', side_effect=AssertionError('Must not load source data')), \
                patch('actionmail.evaluation.cli._run_one', side_effect=AssertionError('Must not infer')):
            self.save_run(Path(temp), 'saved', '2026-10-02')
            self.assertEqual(self.call(['eval', '--saved', '--case', 'S02'])[0], 0)

    def test_explicit_benchmark_and_estimate_are_forwarded_once(self):
        with patch('actionmail.evaluation.cli.main', return_value=0) as evaluate:
            code, output, _ = self.call(['eval', '--benchmark=frozen', '--estimate'])
            self.assertEqual(code, 0)
            self.assertEqual(evaluate.call_args.args[0], ['--benchmark=frozen', '--preflight'])
            self.assertNotIn('v2-60', output)
            self.assertEqual(self.call(['eval', '--estimate', '--validate'])[0], 2)
            self.assertEqual(evaluate.call_count, 1)

    def test_confirmation_decline_and_eof_stop_before_inference(self):
        with TemporaryDirectory() as temp, patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-only'}, clear=True), \
                patch('actionmail.evaluation.cli.APIClient'), \
                patch('actionmail.evaluation.cli._show_preflight', return_value=(0.1, 0.5, 0.0, 'test')), \
                patch('actionmail.evaluation.cli._run_one') as infer:
            target = Path(temp) / 'must-not-exist'
            arguments = ['eval', '--model', 'test-model', '--limit', '1', '--output-dir', str(target)]
            with patch('builtins.input', return_value='n'):
                self.assertEqual(self.call(arguments)[0], 0)
            with patch('builtins.input', side_effect=EOFError):
                code, _, error = self.call(arguments)
                self.assertEqual(code, 1)
                self.assertIn('confirmation input is unavailable', error)
            infer.assert_not_called()
            self.assertFalse(target.exists())

    def test_estimate_and_validate_never_infer(self):
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-only'}, clear=True), \
                patch('actionmail.evaluation.cli.APIClient'), \
                patch('actionmail.evaluation.cli._show_preflight', return_value=(0.1, 0.5, 0.0, 'test')) as estimate, \
                patch('actionmail.evaluation.cli._run_one') as infer:
            self.assertEqual(self.call(['eval', '--model', 'test-model', '--estimate'])[0], 0)
            self.assertEqual(self.call(['eval', '--validate'])[0], 0)
            estimate.assert_called_once()
            infer.assert_not_called()

    def test_simple_commands_help_and_unknown_options(self):
        for command in ('start', 'doctor', 'check', 'review'):
            with self.subTest(command=command), patch.object(cli, 'saved_runs', return_value=[]):
                code, output, _ = self.call([command, '--help'])
                self.assertEqual(code, 0)
                self.assertIn('usage:', output)
        for command in ('start', 'doctor', 'check'):
            self.assertEqual(self.call([command, '--typo'])[0], 2)

    def test_review_preserves_explicit_run_after_options(self):
        with patch('actionmail.interfaces.review_server.main', return_value=0) as review, \
                patch.object(cli, 'saved_runs', side_effect=AssertionError('Explicit run must be preserved')):
            arguments = ['--port', '61934', 'custom-run', '--no-browser']
            self.assertEqual(self.call(['review', *arguments])[0], 0)
            review.assert_called_once_with(arguments)

    def test_analysis_and_legacy_input_share_original_pipeline(self):
        with patch('actionmail.interfaces.cli.main', return_value=0) as analyze:
            arguments = ['examples/sample_email.json', '--schema', 'v2']
            self.assertEqual(self.call(['analyze', *arguments])[0], 0)
            self.assertEqual(self.call(arguments)[0], 0)
            self.assertEqual(analyze.call_args_list[0], analyze.call_args_list[1])

    def test_single_email_confirmation_eof_never_calls_pipeline(self):
        with patch.dict('os.environ', {'ACTIONMAIL_MODEL': 'test-model', 'OPENROUTER_API_KEY': 'test-only'}, clear=True), \
                patch('builtins.input', side_effect=EOFError), \
                patch('actionmail.interfaces.cli.APIClient'), \
                patch('actionmail.interfaces.cli.process_email_multi') as infer:
            code, _, error = self.call(['analyze', str(cli.PROJECT_ROOT / 'examples' / 'sample_email.json'), '--schema', 'v2'])
            self.assertEqual(code, 1)
            self.assertIn('confirmation input is unavailable', error)
            infer.assert_not_called()

    def test_start_menu_exits_without_running_operations(self):
        with patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value='0'), \
                patch.object(cli, '_run_demo') as demo, patch.object(cli, '_evaluation') as evaluate:
            code, output, _ = self.call(['start'])
            self.assertEqual(code, 0)
            self.assertIn('Offline scripted demo', output)
            demo.assert_not_called()
            evaluate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
