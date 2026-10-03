"""Engineering checks using authored Google-shaped fixtures; no live API/model calls."""
import base64
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, Mock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from actionmail.application.service import ApplicationService, CappedModel
from actionmail.application.store import Store, encode_email, decode_email
from actionmail.integrations.auth import GoogleAuth
from actionmail.integrations.calendar import GoogleCalendarAdapter, event_id, export_ics, validate_draft
from actionmail.integrations.demo import DemoGoogleTransport, DemoModel
from actionmail.integrations.google import GoogleTransport, ProviderError, UnknownWrite
from actionmail.integrations.mail import GmailAdapter
from actionmail.interfaces.app_server import create_server
from actionmail.reasoning.api_client import ModelCallError


class V3Tests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / 'app.sqlite3'
        self.fake = DemoGoogleTransport(Path(self.temp.name) / 'events.json')
        self.gmail = GmailAdapter(self.fake)
        self.calendar = GoogleCalendarAdapter(self.fake)
        self.calendar.simulated = True
        self.app = ApplicationService(Store(self.path), DemoModel(), self.calendar)

    def tearDown(self):
        self.temp.cleanup()

    def task(self):
        record = self.app.import_mail(self.gmail.fetch('m1'))
        record = self.app.analyze(record['id'])
        proposal = record['proposals'][0]
        record = self.app.review(record['id'], proposal['id'], 'accepted', 'Edited task', '2026-10-03')
        return record, record['proposals'][0]

    def draft(self):
        record, proposal = self.task()
        fields = {'title': 'Approved deadline', 'description': 'Source mail only', 'all_day': True,
                  'start': '2026-10-03', 'end': '2026-10-04', 'timezone': 'Asia/Singapore', 'calendar_id': 'demo@example.com'}
        record = self.app.save_draft(record['id'], proposal['id'], fields)
        return record, record['proposals'][0], fields

    def test_gmail_target_timestamp_and_attachment_bytes(self):
        mail = self.gmail.fetch('m1')
        self.assertEqual(mail.account, 'demo@example.com')
        self.assertEqual(mail.email.target_recipient, mail.account)
        self.assertEqual(mail.email.received_at.isoformat(), '2026-10-01T09:00:00+08:00')
        self.assertEqual(mail.email.cc_recipients, ('observer@example.com',))
        self.assertEqual(mail.email.external_sources[0].content, b'Include the scope, risks and delivery milestones.')
        self.assertEqual(mail.email.thread[0].source_id, 'thread:1')
        self.assertEqual(decode_email(encode_email(mail.email)), mail.email)

    def test_list_does_not_fetch_body_or_attachment(self):
        self.assertEqual(len(self.gmail.list_messages()['messages']), 3)
        self.assertTrue(all(method == 'GET' and 'format=full' not in url and '/attachments/' not in url
                            for method, url, body in self.fake.calls))
        with self.assertRaises(ValueError):
            self.gmail.list_messages(limit=500)

    def test_selected_historical_boundary_excludes_future_messages(self):
        self.fake.data['history'].reverse()
        mail = self.gmail.fetch('old1')
        self.assertEqual(mail.email.thread, ())
        self.assertEqual(mail.email.body, 'Please prepare the brief for the demo user.')

    def test_html_mime_and_old_attachment_inventory_are_preserved(self):
        old = self.fake.data['history'][0]
        old['payload']['mimeType'] = 'multipart/mixed'
        old['payload']['parts'] = [
            {'mimeType': 'text/html', 'body': {'data': base64.urlsafe_b64encode(b'<p>Earlier request</p><a href="https://example.org/details">details</a>').decode()}},
            {'mimeType': 'text/plain', 'filename': 'history.txt', 'body': {'data': base64.urlsafe_b64encode(b'Old requirements').decode()}}]
        old['payload'].pop('body')
        mail = self.gmail.fetch('m1')
        self.assertIn('Earlier request', mail.email.thread[0].text)
        self.assertIn('thread:1:attachment:1', [s.source_id for s in mail.email.external_sources])
        self.assertIn('thread:1:link:1', [s.source_id for s in mail.email.external_sources])

    def test_permission_denial_surfaces_usable_error(self):
        with patch.object(self.fake, 'request', side_effect=ProviderError(403, 'Permission denied')):
            with self.assertRaisesRegex(ProviderError, 'Permission denied'):
                self.gmail.list_messages()

    def test_all_three_result_states_use_existing_core(self):
        for mid, status in [('m1', 'action'), ('m2', 'no_action'), ('m3', 'needs_review')]:
            record = self.app.import_mail(self.gmail.fetch(mid))
            record = self.app.analyze(record['id'])
            self.assertEqual(record['analysis']['decision']['status'], status)
            self.assertFalse(record['analysis']['validation_errors'])
        self.assertTrue(record['analysis']['decision']['evidence'])

    def test_review_survives_restart_and_unchanged_refresh(self):
        record, proposal = self.task()
        restarted = ApplicationService(Store(self.path), DemoModel(), self.calendar)
        refreshed = restarted.import_mail(self.gmail.fetch('m1'))
        self.assertEqual(refreshed['id'], record['id'])
        self.assertEqual(refreshed['proposals'][0]['text'], 'Edited task')
        self.assertEqual(restarted.tasks()[0]['text'], 'Edited task')
        with patch.object(restarted.model, 'complete', side_effect=AssertionError('No duplicate model call')):
            restarted.analyze(record['id'])

    def test_rejected_task_cannot_draft_or_write(self):
        record, proposal = self.task()
        self.app.review(record['id'], proposal['id'], 'rejected', proposal['text'], None)
        self.assertEqual(self.app.tasks(), [])
        with self.assertRaises(ValueError):
            self.app.save_draft(record['id'], proposal['id'], {})
        with self.assertRaises(ValueError):
            self.app.write(record['id'], proposal['id'])

    def test_confirmation_invalidation_and_cancel(self):
        record, proposal, fields = self.draft()
        revision = proposal['draft']['revision']
        self.app.confirm(record['id'], proposal['id'], revision)
        fields['title'] = 'Changed title'
        changed = self.app.save_draft(record['id'], proposal['id'], fields)
        self.assertEqual(changed['proposals'][0]['draft']['state'], 'draft')
        with self.assertRaises(ValueError):
            self.app.confirm(record['id'], proposal['id'], revision)
        with self.assertRaises(ValueError):
            self.app.write(record['id'], proposal['id'])
        self.app.cancel_draft(record['id'], proposal['id'])
        self.assertFalse(self.fake.events)

    def test_no_write_before_confirmation_and_duplicate_clicks(self):
        record, proposal, fields = self.draft()
        with self.assertRaises(ValueError):
            self.app.write(record['id'], proposal['id'])
        self.app.confirm(record['id'], proposal['id'], proposal['draft']['revision'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.app.write(record['id'], proposal['id']), range(2)))
        self.assertEqual(len(self.fake.events), 1)
        restarted = ApplicationService(Store(self.path), DemoModel(), self.calendar)
        restarted.write(record['id'], proposal['id'])
        self.assertEqual(len([c for c in self.fake.calls if c[0] == 'POST']), 1)
        event = next(iter(self.fake.events.values()))
        self.assertNotIn('attendees', event)
        self.assertEqual(event['transparency'], 'transparent')
        self.assertTrue(results[0]['proposals'][0]['draft']['simulated'])

    def test_timeout_after_send_reconciles_after_restart_without_retry(self):
        record, proposal, fields = self.draft()
        self.app.confirm(record['id'], proposal['id'], proposal['draft']['revision'])
        create = self.calendar.create
        def timeout(draft, key):
            create(draft, key)
            raise UnknownWrite('Timeout after send')
        with patch.object(self.calendar, 'create', side_effect=timeout):
            result = self.app.write(record['id'], proposal['id'])
        self.assertEqual(result['proposals'][0]['draft']['state'], 'unknown')
        fake = DemoGoogleTransport(Path(self.temp.name) / 'events.json')
        calendar = GoogleCalendarAdapter(fake)
        restarted = ApplicationService(Store(self.path), DemoModel(), calendar)
        with self.assertRaises(ValueError):
            restarted.write(record['id'], proposal['id'])
        result = restarted.reconcile(record['id'], proposal['id'])
        self.assertEqual(result['proposals'][0]['draft']['state'], 'written')
        self.assertEqual(len(fake.events), 1)
        self.assertTrue(all(c[0] == 'GET' for c in fake.calls))

    def test_unknown_not_found_stays_locked(self):
        record, proposal, fields = self.draft()
        self.app.confirm(record['id'], proposal['id'], proposal['draft']['revision'])
        with patch.object(self.calendar, 'create', side_effect=UnknownWrite('Timeout')):
            self.app.write(record['id'], proposal['id'])
        result = self.app.reconcile(record['id'], proposal['id'])
        self.assertEqual(result['proposals'][0]['draft']['state'], 'unknown')
        with self.assertRaises(ValueError):
            self.app.confirm(record['id'], proposal['id'], proposal['draft']['revision'])

    def test_write_denial_is_failed_without_blind_retry(self):
        record, proposal, fields = self.draft()
        self.app.confirm(record['id'], proposal['id'], proposal['draft']['revision'])
        with patch.object(self.calendar, 'create', side_effect=ProviderError(403, 'Permission denied')):
            result = self.app.write(record['id'], proposal['id'])
        self.assertEqual(result['proposals'][0]['draft']['state'], 'failed')
        self.assertFalse(self.fake.events)

    def test_crash_recovery_and_call_cap(self):
        record, proposal, fields = self.draft()
        record['state'] = 'analyzing'
        record['proposals'][0]['draft']['state'] = 'writing'
        self.app.store.save(record)
        restarted = ApplicationService(Store(self.path), DemoModel(), self.calendar)
        saved = restarted.store.get(record['id'])
        self.assertEqual(saved['state'], 'failed')
        self.assertEqual(saved['proposals'][0]['draft']['state'], 'unknown')
        with self.assertRaises(ModelCallError):
            CappedModel(DemoModel(), maximum=0).complete('', '')

    def test_null_deadline_remains_task_until_user_provides_dates(self):
        record, proposal = self.task()
        saved = self.app.review(record['id'], proposal['id'], 'accepted', proposal['text'], None)
        self.assertIsNone(saved['proposals'][0]['deadline'])
        with self.assertRaises(ValueError):
            self.app.save_draft(record['id'], proposal['id'], {'title': proposal['text']})

    def test_timezone_validation_and_ics_utf8_folding(self):
        record, proposal, fields = self.draft()
        fields.update(title='邮件任务;' * 50, description='a,b;line\nsecond')
        with self.assertRaises(ValueError):
            self.app.ics(record['id'], proposal['id'])
        self.app.confirm(record['id'], proposal['id'], proposal['draft']['revision'])
        self.assertIn(b'BEGIN:VCALENDAR', self.app.ics(record['id'], proposal['id']))
        saved = self.app.store.get(record['id'])
        self.assertEqual(saved['history'][-1]['operation'], 'ics_export')
        self.assertEqual(saved['proposals'][0]['draft']['state'], 'confirmed')
        result = export_ics(fields, 'stable-key')
        self.assertTrue(all(len(line) <= 75 for line in result.split(b'\r\n')))
        unfolded = result.replace(b'\r\n ', b'').decode()
        self.assertIn('DTEND;VALUE=DATE:20261004', unfolded)
        self.assertIn('a\\,b\\;line\\nsecond', unfolded)
        self.assertIn('UID:' + event_id('stable-key'), unfolded)
        timed = dict(fields, all_day=False, start='2026-10-03T09:00:00+08:00', end='2026-10-03T10:00:00+08:00')
        self.assertIn(b'DTSTART:20261003T010000Z', export_ics(timed, 'timed-key'))
        for change in [{'start': '2026-10-03T09:00:00'}, {'timezone': 'Unknown/Zone'},
                       {'start': '2026-10-03T09:00:00+00:00'}, {'end': '2026-10-03T08:00:00+08:00'}]:
            with self.assertRaises(ValueError):
                validate_draft(dict(timed, **change))

    def test_transport_never_retries_post_or_logs_raw_provider_error(self):
        tokens = Mock()
        tokens.access_token.return_value = 'private-token'
        transport = GoogleTransport(tokens)
        with patch('actionmail.integrations.google.urlopen', side_effect=URLError('sensitive response')) as request:
            with self.assertRaises(UnknownWrite):
                transport.request('POST', 'https://www.googleapis.com/calendar/v3/calendars/primary/events', {})
            self.assertEqual(request.call_count, 1)
        with patch('actionmail.integrations.google.urlopen', side_effect=HTTPError('url', 403, 'secret', {}, None)):
            with self.assertRaisesRegex(ProviderError, 'Permission denied'):
                transport.request('GET', 'https://gmail.googleapis.com/gmail/v1/users/me/profile')
        with self.assertRaises(ValueError):
            transport.request('GET', 'https://example.com/mail')

    def test_disconnect_removes_only_local_feature_token(self):
        auth = GoogleAuth('gmail', self.temp.name)
        auth.path.write_text('private token', encoding='utf-8')
        other = Path(self.temp.name) / 'calendar-token.json'
        other.write_text('calendar token', encoding='utf-8')
        auth.disconnect()
        self.assertFalse(auth.path.exists())
        self.assertTrue(other.exists())

    def test_oauth_refresh_saves_private_token_and_denial_is_clean(self):
        auth = GoogleAuth('gmail', self.temp.name)
        auth.path.write_text('{}', encoding='utf-8')
        credentials = Mock(valid=False, token='refreshed-token')
        credentials.has_scopes.return_value = True
        credentials.to_json.return_value = '{"token":"refreshed-token"}'
        factory = Mock()
        factory.from_authorized_user_file.return_value = credentials
        modules = {'google.oauth2.credentials': Mock(Credentials=factory),
                   'google.auth.transport.requests': Mock(Request=Mock(return_value='mock-refresh-request'))}
        with patch.dict('sys.modules', modules):
            self.assertEqual(auth.access_token(), 'refreshed-token')
            credentials.refresh.assert_called_once_with('mock-refresh-request')
            self.assertEqual(json.loads(auth.path.read_text())['token'], 'refreshed-token')
            credentials.refresh.side_effect = RuntimeError('secret refresh error')
            with self.assertRaisesRegex(ProviderError, 'Token refresh failed'):
                auth.access_token()
            credentials.has_scopes.return_value = False
            with self.assertRaisesRegex(ProviderError, 'required permissions'):
                auth.access_token()

    def test_oauth_calendar_permissions_are_separate_and_denial_saves_nothing(self):
        auth = GoogleAuth('calendar', self.temp.name)
        credentials = Mock()
        credentials.has_scopes.return_value = False
        flow = Mock()
        flow.run_local_server.return_value = credentials
        factory = Mock()
        factory.from_client_secrets_file.return_value = flow
        with patch.dict('sys.modules', {'google_auth_oauthlib.flow': Mock(InstalledAppFlow=factory)}):
            with self.assertRaisesRegex(ProviderError, 'not granted'):
                auth.connect('mock-client.json')
        self.assertFalse(auth.path.exists())
        scopes = factory.from_client_secrets_file.call_args.args[1]
        self.assertTrue(all('gmail' not in scope for scope in scopes))

    def test_duplicate_event_conflict_reuses_matching_operation_only(self):
        record, proposal, fields = self.draft()
        key = proposal['draft']['operation_key']
        first = self.calendar.create(fields, key)
        second = self.calendar.create(fields, key)
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(len(self.fake.events), 1)
        self.fake.events[(fields['calendar_id'], event_id(key))]['extendedProperties'] = {}
        with self.assertRaisesRegex(ProviderError, 'conflict'):
            self.calendar.create(fields, key)

    def test_date_boundary_uses_configured_timezone(self):
        self.fake.data['messages'][0]['internalDate'] = '1790875800000'
        utc = GmailAdapter(self.fake, 'UTC').fetch('m1').email.received_at
        singapore = self.gmail.fetch('m1').email.received_at
        self.assertEqual(utc.timestamp(), singapore.timestamp())
        self.assertNotEqual(utc.date(), singapore.date())

    def test_calendar_account_mismatch_blocks_real_enablement(self):
        self.calendar.validate_account('demo@example.com')
        self.assertEqual(self.calendar.account, 'demo@example.com')
        with self.assertRaisesRegex(ValueError, 'same account'):
            self.calendar.validate_account('different@example.com')

    def test_http_origin_guard_and_product_persistence(self):
        server = create_server(self.app, self.gmail)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f'http://127.0.0.1:{server.server_port}'
        try:
            payload = json.dumps({'message_id': 'm1'}).encode()
            request = Request(origin + '/api/mail/fetch', data=payload, headers={'Content-Type': 'application/json'})
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 403)
            request.add_header('Origin', origin)
            with urlopen(request) as response:
                record = json.load(response)['record']
            with urlopen(origin + '/api/state') as response:
                result = json.load(response)
            self.assertEqual(result['messages'][0]['id'], record['id'])
            self.assertNotIn('content', result['messages'][0]['email']['external_sources'][0])
            with urlopen(origin + '/') as response:
                self.assertIn(b'Accepted tasks', response.read())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
