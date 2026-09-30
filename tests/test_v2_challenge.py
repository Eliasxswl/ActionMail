import base64
import io
import json
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch, MagicMock

from actionmail.content.reader import ReadLimits, read_external_sources, extract
from actionmail.content.links import fetch_allowlisted_https, _PinnedHTTPSConnection
from actionmail.domain.email import EmailPackage, ExternalSource
from actionmail.evaluation.challenge import load_challenge, challenge_checks, prepare_challenge, approve_challenge_gold
from actionmail.evaluation.cli import DEFAULT_MAILEX_ROOT, PROJECT_ROOT, _run_one
from actionmail.evaluation.preflight import estimate
from actionmail.evaluation.review import ReviewDataset
from actionmail.reasoning.model_client import ModelReply
from actionmail.reasoning.api_client import ModelCallError
from actionmail.workflow.coverage import WorkflowLimits, segments
from actionmail.workflow.multi_pipeline import process_email_multi, process_email_multi_with_external

MANIFEST = PROJECT_ROOT / 'evaluation' / 'archive' / 'challenge_v2_1_revision2.jsonl'

def action(quote, sid='body', text='Approve the request.'):
    return {'status': 'action', 'actions': [{'kind': 'perform_task', 'text': text, 'deadline': None,
                                           'evidence': [{'source_id': sid, 'quote': quote}]}], 'review_reason': None}

class ScriptModel:
    def __init__(self, replies):
        self.responses = iter(replies)
        self.calls = []
    def complete(self, system, user):
        self.calls.append((system, user))
        value = next(self.responses)
        return ModelReply(json.dumps(value), 'offline-script', 100, 30, 1)

class V2ChallengeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_challenge(MANIFEST, DEFAULT_MAILEX_ROOT)
        cls.by_id = {c.case_id: c for c in cls.cases}

    def test_real_eml_office_pdf_provenance_and_complete_long_extraction(self):
        for cid, label in [('A01', 'page:2'), ('A02', 'paragraph:2'), ('A03', 'paragraph:2'), ('A04', 'sheet:Logistics!D7')]:
            with self.subTest(cid=cid):
                case = self.by_id[cid]
                out = read_external_sources(case.email)
                self.assertFalse(out.failures)
                self.assertIn(label, [l.label for l in out.records[0].locations])
                self.assertGreater(out.records[0].bytes, 100)
                self.assertTrue(out.records[0].sha256)
                for a in case.gold['actions']:
                    self.assertIn(a['evidence'][0]['quote'], out.records[0].extracted_text)
        self.assertGreater(read_external_sources(self.by_id['A02'].email).records[0].characters, 20_000)

    def test_office_formula_cache_missing_cache_and_external_relationship_not_executed(self):
        src = self.by_id['A04'].email.external_sources[0]
        out = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(src.content)) as zin, zipfile.ZipFile(out, 'w') as zout:
            for name in zin.namelist():
                data = zin.read(name)
                if name == 'xl/worksheets/sheet1.xml':
                    data = data.replace(b'</row>', b'<c r="E1"><f>SUM(2,3)</f><v>5</v></c><c r="F1"><f>WEBSERVICE("https://private.example")</f></c></row>')
                zout.writestr(name, data)
            zout.writestr('xl/worksheets/_rels/sheet1.xml.rels', '<Relationships><Relationship TargetMode="External" Target="https://private.example"/></Relationships>')
        with patch('socket.create_connection', side_effect=AssertionError('Office extraction must not fetch')):
            text, loc = extract(replace(src, content=out.getvalue()))
        self.assertIn('formula (not executed): =SUM(2,3); cached value: 5', text)
        self.assertIn('cached value: [missing]', text)
        self.assertIn('sheet:Finance!E1', [l.label for l in loc])

    def test_generic_attachment_mime_uses_supported_extension_and_records_extractor(self):
        case = self.by_id['A02']
        source = replace(case.email.external_sources[0], media_type='application/octet-stream')
        out = read_external_sources(replace(case.email, external_sources=(source,)))
        self.assertFalse(out.failures)
        self.assertEqual(out.records[0].extraction_method, 'ooxml_paragraphs')
        self.assertIn('wordprocessingml', out.records[0].media_type)
        with self.assertRaisesRegex(ValueError, 'Binary content'):
            extract(replace(source, name='fake.txt', content=b'\x00\x00', media_type='text/plain'))

    def test_archive_bomb_entities_corruption_and_empty_pdf_fail_explicitly(self):
        source = self.by_id['A02'].email.external_sources[0]
        bomb = io.BytesIO()
        with zipfile.ZipFile(bomb, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('word/document.xml', 'a' * 200_000)
        with self.assertRaisesRegex(ValueError, 'compression ratio'):
            extract(replace(source, content=bomb.getvalue()))
        entity = io.BytesIO()
        with zipfile.ZipFile(entity, 'w') as z:
            z.writestr('word/document.xml', '<!DOCTYPE a [<!ENTITY b "evil">]><a>&b;</a>')
        with self.assertRaisesRegex(ValueError, 'entities'):
            extract(replace(source, content=entity.getvalue()))
        for cid in ('A08', 'H02'):
            outcome = read_external_sources(self.by_id[cid].email)
            self.assertTrue(outcome.failures)
            self.assertFalse(outcome.records)

    def test_encrypted_pdf_and_login_or_dynamic_page_require_explicit_review(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.encrypt('offline-test-password')
        out = io.BytesIO()
        writer.write(out)
        src = self.by_id['A01'].email.external_sources[0]
        with self.assertRaisesRegex(ValueError, 'Encrypted PDF'):
            extract(replace(src, content=out.getvalue()))
        for html in (b'<form><input type="password">Sign in to continue</form>', b'<script>renderApp()</script>Please enable JavaScript', b'<script>renderApp()</script>'):
            with self.subTest(html=html), self.assertRaisesRegex(ValueError, 'manual review'):
                extract(replace(src, content=html, media_type='text/html'))

    def test_validated_plan_skips_unreadable_irrelevant_source_and_selects_three_documents(self):
        case = self.by_id['A06']
        model = ScriptModel([{'sources': [{'source_id': 'attachment:1', 'relevance': 'irrelevant', 'reason': 'Sender explicitly says unrelated advertising'}]}, case.gold])
        run = process_email_multi_with_external(case.email, model)
        self.assertEqual(run.decision.status, 'action')
        self.assertFalse(run.read_records)
        self.assertEqual(run.source_plan[0].relevance, 'irrelevant')
        self.assertEqual(len(model.calls), 2)
        case = self.by_id['A05']
        plan = {'sources': [{'source_id': sid, 'relevance': e['relevance'], 'reason': 'Assigned task or reference context'} for sid,e in case.record['source_expectations'].items()]}
        run = process_email_multi_with_external(case.email, ScriptModel([plan, case.gold]))
        self.assertEqual(len(run.read_records), 3)
        self.assertEqual(run.decision.action_count, 2)
        self.assertTrue(challenge_checks(case, run)['content_coverage_complete'])
        self.assertIsNone(challenge_checks(case, run)['status_correct'])

    def test_unknown_plan_ids_unresolved_and_decisive_failure_never_become_no_action(self):
        case = self.by_id['A08']
        for sid, relevance in [('made-up:1', 'decisive'), ('attachment:1', 'unresolved'), ('attachment:1', 'decisive')]:
            with self.subTest(sid=sid, relevance=relevance):
                model = ScriptModel([{'sources': [{'source_id': sid, 'relevance': relevance, 'reason': 'Cannot determine assignment'}]}])
                run = process_email_multi_with_external(case.email, model)
                self.assertEqual(run.decision.status, 'needs_review')
                self.assertEqual(len(model.calls), 1)
        run = process_email_multi_with_external(self.by_id['A05'].email, ScriptModel([{'sources': [{'source_id': sid, 'relevance': 'decisive', 'reason': 'Required'} for sid in self.by_id['A05'].record['source_expectations']]}]), read_limits=ReadLimits(max_sources=2))
        self.assertIn('budget', run.decision.review_reason)

    def test_api_failure_after_planning_preserves_prior_usage_and_failed_call_trace(self):
        case = self.by_id['A01']
        plan = {'sources': [{'source_id': 'attachment:1', 'relevance': 'decisive', 'reason': 'Required page assignment'}]}
        model = ScriptModel([plan])
        original = model.complete
        def complete(system, user):
            if model.calls:
                raise ModelCallError('offline simulated timeout')
            return original(system, user)
        model.complete = complete
        row = _run_one(case, 'llm', model, (.1, .5, 0), 'snapshots', (), 'v2')
        self.assertEqual(row['prediction']['status'], 'needs_review')
        self.assertEqual(row['model_calls'], 2)
        self.assertEqual(row['model_calls_succeeded'], 1)
        self.assertEqual(row['failed_model_calls'], 1)
        self.assertEqual(row['usage']['input_tokens'], 100)
        self.assertEqual(len(row['raw_model_responses']), 1)
        self.assertIn('timeout', row['error'])
        self.assertIsNone(row['estimated_cost_usd'])
        self.assertFalse(row['content_coverage_complete'])

    def test_long_end_request_split_overlap_and_merge_validates_only_submitted_evidence(self):
        case = self.by_id['L06']
        windows = segments(case.email.sources())
        q = case.gold['actions'][0]['evidence'][0]['quote']
        self.assertTrue(any(q in w.text for w in windows))
        start = case.email.body.index(q)
        self.assertLess(start, 8000)
        self.assertGreater(start + len(q), 8000)
        self.assertTrue(any(w.source_id == 'body' and w.start > 0 and q in w.text for w in windows))
        responses = [case.gold if q in w.text else {'status': 'no_action', 'actions': [], 'review_reason': None} for w in windows]
        model = ScriptModel(responses + [case.gold])
        run = process_email_multi(case.email, model)
        self.assertEqual(run.decision.status, 'action')
        self.assertEqual(len(run.coverage), len(windows))
        self.assertTrue(challenge_checks(case, run)['content_coverage_complete'])
        # A quote exists somewhere in the source but was not in the merge ledger.
        invented = action(case.email.body[100:150])
        strict_limits = WorkflowLimits(segment_chars=4000)
        strict_responses = [case.gold if q in w.text else {'status': 'no_action', 'actions': [], 'review_reason': None} for w in segments(case.email.sources(), strict_limits)]
        run = process_email_multi(case.email, ScriptModel(strict_responses + [invented]), limits=strict_limits)
        self.assertEqual(run.decision.status, 'needs_review')
        self.assertIn('ledger', run.decision.review_reason)
        # Boundary coverage is complete, with no skipped suffix.
        for sid, text in case.email.sources().items():
            selected = [w for w in windows if w.source_id == sid]
            self.assertEqual(selected[0].start, 0)
            self.assertEqual(selected[-1].end, len(text))
            self.assertTrue(all(b.start <= a.end for a,b in zip(selected, selected[1:])))

    def test_budget_guard_preserves_prediction_without_call_and_four_actions_require_review(self):
        case = self.by_id['H04']
        model = ScriptModel([])
        row = _run_one(case, 'llm', model, (0.1, 0.5, 0), 'snapshots', (), 'v2')
        self.assertEqual(row['prediction']['status'], 'needs_review')
        self.assertEqual(row['model_calls'], 0)
        self.assertIn('unread', row['prediction']['review_reason'])
        self.assertFalse(row['content_coverage_complete'])
        self.assertIsNone(row['status_correct'])
        body = 'Alex, send the minutes. Alex, update the schedule. Alex, approve the budget. Alex, book the venue.'
        email = replace(case.email, body=body)
        value = {'status': 'action', 'review_reason': None, 'actions': [action(q)['actions'][0] | {'text': q} for q in body.split(' Alex, ')]}
        # Use exact source evidence for each independent request.
        value['actions'] = [action(q, text=q)['actions'][0] for q in [s.strip() + '.' for s in body.split('.') if s.strip()]]
        run = process_email_multi(email, ScriptModel([value]))
        self.assertEqual(run.decision.status, 'needs_review')
        self.assertEqual(run.decision.action_count, 0)

    def test_reference_review_and_preflight_use_separate_denominator_without_model_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'gold-preview'
            prepare_challenge(self.cases, MANIFEST, output)
            ds = ReviewDataset.open(output, MANIFEST, DEFAULT_MAILEX_ROOT)
            self.assertEqual(len(ds.overview()['cases']), 24)
            detail = ds.detail('A04')
            self.assertEqual(detail['reference_review_state'], 'pending_owner')
            self.assertIn('Alex, book the review room.', detail['external_sources'][0]['text'])
            self.assertIsNone(detail['prediction'])
            approved = Path(tmp) / 'approved.jsonl'
            with self.assertRaises(OSError):
                approve_challenge_gold(MANIFEST, output, approved)
            ds.save_review('A04', {'action_meaning': '', 'evidence_support': '', 'gold_label': 'correct', 'note': ''})
            with self.assertRaisesRegex(ValueError, 'Every challenge reference'):
                approve_challenge_gold(MANIFEST, output, approved)
            # Synthetic test adjudication in a temporary directory, never real owner records.
            for cid in ds.cases:
                ds.save_review(cid, {'action_meaning': '', 'evidence_support': '', 'gold_label': 'correct', 'note': ''})
            approve_challenge_gold(MANIFEST, output, approved)
            self.assertTrue(all(json.loads(line)['review_state'] == 'approved' for line in approved.read_text(encoding='utf-8').splitlines()))
            self.assertTrue(all(c.record['review_state'] == 'pending_owner' for c in self.cases))
        short = estimate([self.by_id['A01']], Path('/nonexistent'), 'offline', .1, .5, external_mode='snapshots', schema='v2')
        long = estimate([self.by_id['A02']], Path('/nonexistent'), 'offline', .1, .5, external_mode='snapshots', schema='v2')
        self.assertGreater(long['model_calls'], short['model_calls'])
        self.assertGreater(long['input_tokens'], short['input_tokens'])

class LiveTransportTests(unittest.TestCase):
    def transport(self, replies, url='https://public.example/task', domains=('public.example',)):
        connections = []
        def factory(host, address):
            conn = MagicMock()
            status, headers, content = next(replies)
            response = MagicMock()
            response.status = status
            response.getheader.side_effect = lambda key, default=None: headers.get(key, default)
            response.read.return_value = content
            conn.getresponse.return_value = response
            connections.append((host, address, conn))
            return conn
        with patch('actionmail.content.links.socket.getaddrinfo', return_value=[(None,None,None,None,('8.8.8.8',443))]), patch('actionmail.content.links._PinnedHTTPSConnection', side_effect=factory):
            fetched = fetch_allowlisted_https(url, domains)
        return fetched, connections

    def test_redirect_rechecks_destinations_trace_replay_and_connection_cleanup(self):
        replies = iter([(302, {'Location': '/final'}, b''), (200, {'Content-Type': 'text/plain; charset=utf-8'}, b'Alex, send the plan.')])
        fetched, connections = self.transport(replies)
        self.assertEqual(fetched.final_url, 'https://public.example/final')
        self.assertTrue(fetched.retrieved_at.endswith('+00:00'))
        self.assertTrue(all(c.close.called for _,_,c in connections))
        self.assertTrue(all(address == '8.8.8.8' for _,address,_ in connections))
        src = ExternalSource('link:1', 'link', 'https://public.example/task')
        email = EmailPackage('live', 'alex@example.com', None, 'maya@example.com', ('alex@example.com',), 'Task', 'See the task page.', external_sources=(src,))
        out = read_external_sources(email, fetch_live=lambda url: fetched)
        self.assertEqual(base64.b64decode(out.records[0].replay_base64), fetched.content)
        self.assertEqual(out.records[0].final_url, fetched.final_url)
        self.assertEqual(out.email.read_sources[0].text, 'Alex, send the plan.')

    def test_blocked_redirect_content_type_status_compression_size_timeout_and_redirect_limit(self):
        scenarios = [([(302, {'Location': 'https://other.example/final'}, b'')], 'allowlist'),
                     ([(302, {'Location': 'https://127.0.0.1/final'}, b'')], 'allowlist'),
                     ([(200, {'Content-Type': 'application/javascript'}, b'x')], 'content type'),
                     ([(401, {}, b'')], 'HTTP 401'),
                     ([(200, {'Content-Type': 'text/plain', 'Content-Encoding': 'gzip'}, b'x')], 'Compressed'),
                     ([(200, {'Content-Type': 'text/plain'}, b'x' * (2 * 1024 * 1024 + 1))], '2 MiB'),
                     ([(302, {'Location': '/next'}, b'')] * 3, 'redirect')]
        for replies, reason in scenarios:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                self.transport(iter(replies))
        with patch('actionmail.content.links.socket.getaddrinfo', return_value=[(None,None,None,None,('8.8.8.8',443))]), patch('actionmail.content.links._PinnedHTTPSConnection') as factory:
            factory.return_value.getresponse.side_effect = TimeoutError('timed out')
            with self.assertRaises(TimeoutError):
                fetch_allowlisted_https('https://public.example/task', ('public.example',))
            factory.return_value.close.assert_called_once()
        for url in ['http://public.example/task', 'https://user:pass@public.example/task', 'https://public.example:444/task']:
            with self.assertRaises(ValueError):
                fetch_allowlisted_https(url, ('public.example',))
        with patch('actionmail.content.links.socket.getaddrinfo', return_value=[(None,None,None,None,('8.8.8.8',443)), (None,None,None,None,('10.0.0.2',443))]):
            with self.assertRaisesRegex(ValueError, 'non-public'):
                fetch_allowlisted_https('https://public.example/task', ('public.example',))

    def test_tls_connects_to_pinned_ip_with_original_hostname_and_closes_on_error(self):
        conn = _PinnedHTTPSConnection('public.example', '8.8.8.8')
        with patch('actionmail.content.links.socket.create_connection') as create:
            conn._context = MagicMock()
            conn.connect()
            create.assert_called_once_with(('8.8.8.8', 443), 10)
            conn._context.wrap_socket.assert_called_once_with(create.return_value, server_hostname='public.example')
            conn._context.wrap_socket.side_effect = OSError('TLS failure')
            with self.assertRaises(OSError):
                conn.connect()
            create.return_value.close.assert_called_once()

    def test_review_port_rejects_second_listener(self):
        from actionmail.interfaces.review_server import create_server
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'preview'
            cases = load_challenge(MANIFEST, DEFAULT_MAILEX_ROOT)
            prepare_challenge(cases, MANIFEST, output)
            dataset = ReviewDataset.open(output, MANIFEST, DEFAULT_MAILEX_ROOT)
            first = create_server(dataset)
            try:
                with self.assertRaises(OSError):
                    create_server(dataset, first.server_port)
            finally:
                first.server_close()

if __name__ == '__main__':
    unittest.main()
