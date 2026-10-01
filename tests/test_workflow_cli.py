"""CLI integration checks: persistent operations, review gates and safe artifacts."""
import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory

from actionmail.interfaces.workflow_cli import main


class WorkflowCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = self.root / 'cli.sqlite3'

    def tearDown(self):
        self.temp.cleanup()

    def call(self, *args, store=True):
        output, error = io.StringIO(), io.StringIO()
        argv = (['--store', str(self.store)] if store else []) + list(args)
        with redirect_stdout(output), redirect_stderr(error):
            code = main(argv)
        return code, json.loads(output.getvalue() if code == 0 else error.getvalue())

    def record(self):
        code, value = self.call('fetch', 'm1')
        self.assertEqual(code, 0)
        record_id = value['result']['id']
        code, value = self.call('analyze', record_id)
        self.assertEqual(code, 0)
        return record_id, value['result']['proposals'][0]['id']

    def test_one_command_demo_is_offline_inspectable_and_refuses_overwrite(self):
        output = self.root / 'demo'
        code, value = self.call('demo', '--output-dir', str(output), store=False)
        self.assertEqual(code, 0)
        summary = value['result']
        self.assertEqual([s['status'] for s in summary['scenarios']], ['action', 'no_action', 'needs_review'])
        self.assertEqual(summary['real_model_calls'], 0)
        self.assertEqual(summary['real_provider_requests'], 0)
        self.assertEqual(summary['simulated_events'], 1)
        self.assertEqual(summary['simulated_write_requests'], 1)
        records = json.loads((output / 'records.json').read_text(encoding='utf-8'))
        self.assertTrue(records[0]['analysis']['read_records'])
        self.assertTrue(records[0]['analysis']['replies'])
        self.assertNotIn('content', records[0]['email']['external_sources'][0])
        self.assertIn(b'BEGIN:VCALENDAR\r\n', (output / 'deadline.ics').read_bytes())
        original = (output / 'records.json').read_bytes()
        self.assertEqual(self.call('demo', '--output-dir', str(output), store=False)[0], 1)
        self.assertEqual((output / 'records.json').read_bytes(), original)

    def test_commands_reopen_store_and_rejection_blocks_calendar(self):
        record_id, proposal_id = self.record()
        self.assertEqual(self.call('show', record_id)[1]['result']['state'], 'analyzed')
        self.assertEqual(self.call('review', record_id, proposal_id, '--state', 'rejected')[0], 0)
        self.assertEqual(self.call('tasks')[1]['result'], [])
        self.assertEqual(self.call('simulate-write', record_id, proposal_id)[0], 1)
        self.assertEqual(self.call('show', record_id)[1]['result']['proposals'][0]['state'], 'rejected')

    def test_confirmation_revision_and_export_are_enforced_across_commands(self):
        record_id, proposal_id = self.record()
        self.call('review', record_id, proposal_id, '--state', 'accepted')
        fields = self.root / 'fields.json'
        fields.write_text(json.dumps({'title': 'Deadline', 'description': 'Synthetic', 'all_day': True,
                                    'start': '2026-10-03', 'end': '2026-10-04',
                                    'timezone': 'Asia/Singapore', 'calendar_id': 'demo@example.com'}), encoding='utf-8')
        self.assertEqual(self.call('draft', record_id, proposal_id, '--fields', str(fields))[0], 0)
        output = self.root / 'task.ics'
        self.assertEqual(self.call('export', record_id, proposal_id, '--output', str(output))[0], 1)
        self.assertFalse(output.exists())
        revision = self.call('show', record_id)[1]['result']['proposals'][0]['draft']['revision']
        self.assertEqual(self.call('confirm', record_id, proposal_id, '--revision', 'stale')[0], 1)
        self.assertEqual(self.call('confirm', record_id, proposal_id, '--revision', revision)[0], 0)
        self.assertEqual(self.call('export', record_id, proposal_id, '--output', str(output))[0], 0)
        original = output.read_bytes()
        self.assertEqual(self.call('export', record_id, proposal_id, '--output', str(output))[0], 1)
        self.assertEqual(output.read_bytes(), original)
        for _ in range(2):
            self.assertEqual(self.call('simulate-write', record_id, proposal_id)[0], 0)
        events = json.loads(self.store.with_suffix('.demo-events.json').read_text(encoding='utf-8'))
        self.assertEqual(len(events), 1)

    def test_invalid_synthetic_message_returns_error_without_traceback(self):
        code, value = self.call('fetch', 'does-not-exist')
        self.assertEqual(code, 1)
        self.assertIn('Synthetic resource not found', value['error'])


if __name__ == '__main__':
    unittest.main()
