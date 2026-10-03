"""Local product mailbox/review UI. Demo is the default; live features are opt-in."""
import argparse
import base64
import hashlib
import json
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

from actionmail.application.service import ApplicationService
from actionmail.application.store import Store
from actionmail.ingestion.eml import load_eml_bytes
from actionmail.integrations.auth import GoogleAuth, private_home
from actionmail.integrations.calendar import GoogleCalendarAdapter
from actionmail.integrations.demo import DemoGoogleTransport, DemoModel
from actionmail.integrations.google import GoogleTransport, ProviderError
from actionmail.integrations.mail import GmailAdapter, MailRecord
from actionmail.interfaces.review_server import ReviewHTTPServer
from http.server import BaseHTTPRequestHandler

STATIC = {'/': ('app_index.html', 'text/html; charset=utf-8'),
          '/app.js': ('product_app.js', 'text/javascript; charset=utf-8'),
          '/style.css': ('product_style.css', 'text/css; charset=utf-8')}


def public_record(record):
    record = dict(record)
    record['email'] = dict(record['email'])
    record['email']['external_sources'] = [{k: v for k, v in source.items() if k != 'content'}
                                          for source in record['email']['external_sources']]
    return record


def create_server(service, mail, *, port=0, demo=True):
    class Handler(BaseHTTPRequestHandler):
        def send(self, status, content, media):
            self.send_response(status)
            self.send_header('Content-Type', media)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            if media.startswith('text/calendar'):
                self.send_header('Content-Disposition', 'attachment; filename="actionmail.ics"')
            self.end_headers()
            self.wfile.write(content)

        def json(self, status, value):
            self.send(status, json.dumps(value, ensure_ascii=False).encode(), 'application/json; charset=utf-8')

        def allowed(self, mutation=False):
            host = f'127.0.0.1:{self.server.server_port}'
            return self.headers.get('Host') == host and (not mutation or self.headers.get('Origin') == 'http://' + host)

        def do_GET(self):
            if not self.allowed():
                self.json(403, {'error': 'Local access only'})
                return
            path = urlsplit(self.path).path
            try:
                if path in STATIC:
                    name, media = STATIC[path]
                    self.send(200, (Path(__file__).parent / name).read_bytes(), media)
                elif path == '/api/state':
                    self.json(200, {'demo': demo, 'model_simulated': bool(getattr(service.model, 'simulated', False)),
                                    'calendar_account': getattr(service.calendar, 'account', None),
                                    'calendar_enabled': service.calendar is not None, 'mail_connected': self.server.mail_enabled,
                                    'messages': [public_record(r) for r in service.store.all()], 'tasks': service.tasks()})
                elif path == '/api/calendars':
                    self.json(200, {'calendars': service.calendar.list_calendars() if service.calendar else []})
                else:
                    self.json(404, {'error': 'Not found'})
            except (ValueError, KeyError, ProviderError) as exc:
                self.json(400, {'error': str(exc)})

        def do_POST(self):
            if not self.allowed(True):
                self.json(403, {'error': 'Local access only'})
                return
            try:
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('JSON is required')
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 28 * 1024 * 1024:
                    raise ValueError('Request empty or too large')
                value = json.loads(self.rfile.read(size))
                if not isinstance(value, dict):
                    raise ValueError('Request must be an object')
                path = urlsplit(self.path).path
                if path == '/api/mail/list':
                    if not self.server.mail_enabled:
                        raise ValueError('Mailbox disconnected')
                    self.json(200, mail.list_messages(page_token=value.get('page_token')))
                    return
                if path == '/api/mail/fetch':
                    if not self.server.mail_enabled:
                        raise ValueError('Mailbox disconnected')
                    record = service.import_mail(mail.fetch(value['message_id']))
                elif path == '/api/mail/disconnect':
                    self.server.mail_enabled = False
                    if not demo:
                        GoogleAuth('gmail').disconnect()
                    self.json(200, {'disconnected': True})
                    return
                elif path == '/api/calendar/disconnect':
                    service.calendar = None
                    if not demo:
                        GoogleAuth('calendar').disconnect()
                    self.json(200, {'disconnected': True})
                    return
                elif path == '/api/import':
                    content = base64.b64decode(value['eml_base64'], validate=True)
                    if len(content) > 20 * 1024 * 1024:
                        raise ValueError('EML exceeds 20 MB')
                    target = value['recipient'].strip()
                    if '@' not in target:
                        raise ValueError('Provide the target recipient address')
                    digest = hashlib.sha256(content).hexdigest()
                    email = load_eml_bytes(content, target, case_id=digest)
                    record = service.import_mail(MailRecord('local', target, digest, '', '', email))
                else:
                    record_id, proposal_id = value['record_id'], value.get('proposal_id')
                    if path == '/api/analyze':
                        record = service.analyze(record_id, force=value.get('force') is True)
                    elif path == '/api/review':
                        record = service.review(record_id, proposal_id, value['state'], value['text'], value.get('deadline'))
                    elif path == '/api/draft':
                        record = service.save_draft(record_id, proposal_id, value['fields'])
                    elif path == '/api/confirm':
                        record = service.confirm(record_id, proposal_id, value['revision'])
                    elif path == '/api/write':
                        record = service.write(record_id, proposal_id)
                    elif path == '/api/reconcile':
                        record = service.reconcile(record_id, proposal_id)
                    elif path == '/api/cancel':
                        record = service.cancel_draft(record_id, proposal_id)
                    elif path == '/api/export':
                        self.send(200, service.ics(record_id, proposal_id), 'text/calendar; charset=utf-8')
                        return
                    else:
                        self.json(404, {'error': 'Not found'})
                        return
                self.json(200, {'record': public_record(record)})
            except (ValueError, TypeError, KeyError, ProviderError) as exc:
                self.json(400, {'error': str(exc)})
            except Exception:
                self.json(500, {'error': 'Operation failed; saved state is retained. Check local configuration.'})

        def log_message(self, *args):
            pass

    server = ReviewHTTPServer(('127.0.0.1', port), Handler)
    server.mail_enabled = True
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description='ActionMail product UI (offline simulation by default).')
    parser.add_argument('--gmail', action='store_true', help='Use an explicitly authorized real Gmail account')
    parser.add_argument('--calendar', action='store_true', help='Enable real Calendar writes after separate OAuth')
    parser.add_argument('--live-model', action='store_true', help='Enable paid mail transmission on Analyze clicks')
    parser.add_argument('--store', type=Path)
    parser.add_argument('--timezone', default='Asia/Singapore', help='IANA timezone for received-time interpretation')
    parser.add_argument('--port', type=int, default=61933)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args(argv)
    if args.calendar and not args.gmail:
        parser.error('--calendar requires --gmail; keep demo and real calendar records separate')
    try:
        demo = not args.gmail
        store_path = args.store or private_home() / ('demo.sqlite3' if demo else 'app.sqlite3')
        transport = DemoGoogleTransport(store_path.with_suffix('.demo-events.json')) if demo else GoogleTransport(GoogleAuth('gmail'))
        mail = GmailAdapter(transport, args.timezone)
        calendar = GoogleCalendarAdapter(transport) if demo else (
            GoogleCalendarAdapter(GoogleTransport(GoogleAuth('calendar'))) if args.calendar else None)
        if demo:
            calendar.simulated = True
            calendar.account = 'demo@example.com'
        elif calendar:
            calendar.validate_account(mail.profile())
        model = DemoModel()
        if args.live_model:
            import os
            from actionmail.reasoning.api_client import APIClient
            model = APIClient('https://openrouter.ai/api/v1/chat/completions', os.environ.get('OPENROUTER_API_KEY', ''),
                              os.environ.get('ACTIONMAIL_MODEL', 'openai/gpt-6-luna'))
        store = Store(store_path)
        service = ApplicationService(store, model, calendar)
        server = create_server(service, mail, port=args.port, demo=demo)
        url = f'http://127.0.0.1:{server.server_port}/'
        print(('Offline simulated Google mailbox' if demo else 'Gmail mode') + ': ' + url)
        if not args.no_browser:
            webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, ProviderError) as exc:
        print(f'Unable to start: {exc}', file=sys.stderr)
        return 1
    except ImportError:
        print('Install optional Google dependencies before enabling the real account.', file=sys.stderr)
        return 1
    finally:
        if 'server' in locals():
            server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
