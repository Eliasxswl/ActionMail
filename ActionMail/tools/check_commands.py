"""Run CLI acceptance checks in temporary stores with loopback-only networking.

Exercises installed entry points, prompts, HTTP servers and workflow transitions.
Uses a scripted local chat API; these checks do not measure model accuracy.
Requires an editable installation and the existing experiment dependencies.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

PRODUCT = Path(__file__).resolve().parents[1]
ROOT = PRODUCT.parent


class Checks:
    def __init__(self, temporary):
        self.temp = Path(temporary)
        self.results = []
        self.calls = 0
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith(('OPENROUTER_', 'ACTIONMAIL_')):
                del self.env[key]
        self.env.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                        ACTIONMAIL_PRIVATE_DIR=str(self.temp / 'private'),
                        NO_PROXY='127.0.0.1,localhost')
        guard = self.temp / 'guard'
        guard.mkdir()
        (guard / 'sitecustomize.py').write_text(
            "import socket\n"
            "_connect = socket.socket.connect\n"
            "def connect(self, address):\n"
            "    if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1', 'localhost'):\n"
            "        raise OSError('Command check blocks non-loopback connections')\n"
            "    return _connect(self, address)\n"
            "socket.socket.connect = connect\n", encoding='utf-8')
        self.env['PYTHONPATH'] = str(guard)

    def entry(self, name):
        path = Path(sys.executable).parent / (name + ('.exe' if os.name == 'nt' else ''))
        if not path.exists():
            raise RuntimeError(f'Install the editable product first: missing {name}')
        return [str(path)]

    def run(self, label, command, *, expected=0, contains=None, stdin='', cwd=ROOT, env=None):
        started = time.monotonic()
        try:
            process = subprocess.run([str(x) for x in command], cwd=cwd,
                                     env=env or self.env, input=stdin, text=True,
                                     encoding='utf-8', capture_output=True, timeout=90)
            output = process.stdout + process.stderr
            assert process.returncode == expected, f'exit {process.returncode}, expected {expected}: {output[-1800:]}'
            assert contains is None or contains in output, f'missing {contains!r}: {output[-1800:]}'
        except Exception as exc:
            self.results.append({'check': label, 'passed': False, 'error': str(exc)})
            print(f'FAIL {label}: {exc}', flush=True)
            raise
        self.results.append({'check': label, 'passed': True, 'exit_code': process.returncode,
                             'seconds': round(time.monotonic() - started, 3)})
        print(f'PASS {label}', flush=True)
        return process.stdout

    def server(self, label, command, endpoints):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        child = subprocess.Popen([str(x) for x in command] + ['--port', str(port), '--no-browser'],
                                 cwd=ROOT, env=self.env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, encoding='utf-8')
        try:
            deadline = time.monotonic() + 15
            while True:
                try:
                    with urlopen(f'http://127.0.0.1:{port}/', timeout=1) as response:
                        assert response.status == 200
                    break
                except OSError:
                    if child.poll() is not None:
                        raise RuntimeError('Server exited: ' + ''.join(child.communicate()))
                    if time.monotonic() > deadline:
                        raise RuntimeError('Server startup timed out')
                    time.sleep(0.1)
            for endpoint in endpoints:
                with urlopen(f'http://127.0.0.1:{port}{endpoint}', timeout=5) as response:
                    assert response.status == 200
                    if endpoint.startswith('/api/'):
                        payload = json.load(response)
                        if endpoint == '/api/cases':
                            assert len(payload['cases']) == 60
            self.results.append({'check': label, 'passed': True, 'endpoints': endpoints})
            print(f'PASS {label}', flush=True)
        except Exception as exc:
            self.results.append({'check': label, 'passed': False, 'error': str(exc)})
            raise
        finally:
            child.terminate()
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.communicate()

    def execute(self):
        short = self.entry('actionmail')
        workflow = self.entry('actionmail-workflow')
        experiment = [sys.executable, ROOT / 'experiments/code/pipeline.py']
        for entry in ('actionmail', 'actionmail-eval', 'actionmail-review', 'actionmail-app',
                      'actionmail-workflow', 'actionmail-google-auth'):
            self.run(f'{entry} --help', self.entry(entry) + ['--help'])
        for name in ('start', 'demo', 'analyze', 'eval', 'results', 'check', 'doctor', 'ui', 'review'):
            self.run(f'actionmail {name} --help', short + [name, '--help'])
        for name in ('demo', 'mailbox', 'fetch', 'import', 'list', 'tasks', 'show', 'analyze',
                     'review', 'draft', 'confirm', 'export', 'simulate-write'):
            self.run(f'workflow {name} --help', workflow + [name, '--help'])
        for name in ('prepare', 'plan', 'run', 'smoke-bundle', 'score', 'review-score',
                     'mechanism', 'inspect', 'screen', 'reconcile', 'stage2-config'):
            self.run(f'experiment {name} --help', experiment + [name, '--help'])
        self.run('experiment --help', experiment + ['--help'])
        self.run('no-argument piped invocation', short, contains='command')
        self.run('start without terminal', short + ['start'], contains='command')
        self.run('interactive menu: demo, results, exit', [sys.executable, '-c',
                 'import sys; from actionmail.cli import main; sys.stdin.isatty=lambda: True; raise SystemExit(main(["start"]))'],
                 stdin='1\n3\n0\n', contains='simulated_events')
        for name in ('doctor', 'check', 'results'):
            self.run(f'actionmail {name}', short + [name])
        for options in (['--all'], ['--json'], ['--case', 'S02', '--trace'],
                        ['--run', 'v2-regression-repair-20261001', '--case', 'S02']):
            self.run('results ' + ' '.join(options), short + ['results', *options])
        self.run('eval saved', short + ['eval', '--saved'])
        self.run('eval 60-case validation', short + ['eval', '--validate'], contains='60 active v2 cases')
        self.run('eval frozen 50-case validation', self.entry('actionmail-eval') + ['--validate'], contains='50 frozen cases')
        self.run('eval supplementary validation', self.entry('actionmail-eval') + ['--validate', '--benchmark', 'supplement-v2'], contains='10 supplement-v2 cases')
        self.run('legacy evaluation history', self.entry('actionmail-eval') + ['--history'])
        demo = self.temp / 'demo'
        self.run('demo custom output', short + ['demo', '--output-dir', demo])
        summary = json.loads((demo / 'summary.json').read_text())
        assert summary['real_model_calls'] == summary['real_provider_requests'] == 0
        assert summary['simulated_events'] == summary['simulated_write_requests'] == 1
        assert all((demo / name).exists() for name in summary['artifacts'])
        self.run('demo refuses existing directory', short + ['demo', '--output-dir', demo], expected=1)
        self.run('missing model configuration', short + ['analyze', PRODUCT / 'examples/sample_email.json'], expected=1, contains='Set ACTIONMAIL_MODEL')
        self.run('missing EML recipient', short + ['analyze', PRODUCT / 'evaluation/archive/fixtures_v2_1/A04.eml'], expected=1, contains='--recipient is required')
        self.run('invalid action limit', short + ['analyze', PRODUCT / 'examples/sample_email.json', '--schema', 'v2', '--max-actions', '4'], expected=1)
        self.run('live links require allowlist', short + ['analyze', PRODUCT / 'examples/sample_email.json', '--external-mode', 'allowed-live'], expected=1)
        rules = self.temp / 'rules'
        self.run('offline 50-case rule evaluation', short + ['eval', '--benchmark', 'frozen', '--engine', 'rules', '--output-dir', rules], contains='Saved 50 case result(s)')
        self.run('rule evaluation resume', short + ['eval', '--benchmark', 'frozen', '--engine', 'rules', '--output-dir', rules, '--resume'], contains='Saved 50 case result(s)')
        self.run('eval missing live configuration', short + ['eval'], expected=1)
        self.run('conflicting eval shortcuts', short + ['eval', '--estimate', '--validate'], expected=2)
        self.run('trace requires case', short + ['results', '--trace'], expected=2)
        self.run('unknown saved case', short + ['results', '--case', 'MISSING'], expected=1)
        self.workflow_checks(workflow)
        self.model_checks(short)
        self.server('product UI starts and serves assets/API', short + ['ui', '--store', self.temp / 'ui.sqlite3'],
                    ['/app.js', '/style.css', '/api/state', '/api/calendars'])
        self.server('review starts and serves 60 original cases', short + ['review'],
                    ['/app.js', '/style.css', '/api/cases', '/api/cases/S02'])
        self.server('long product UI entry point', self.entry('actionmail-app') + ['--store', self.temp / 'long-ui.sqlite3'], ['/api/state'])
        self.server('long review entry point', self.entry('actionmail-review') + [PRODUCT / 'results/evaluation/v2-regression-repair-20261001'], ['/api/cases'])
        self.run('calendar flag requires Gmail', short + ['ui', '--calendar'], expected=2)
        auth = self.entry('actionmail-google-auth')
        for feature in ('gmail', 'calendar'):
            self.run(f'Google {feature} connect requires client file', auth + ['connect', feature], expected=2)
            self.run(f'Google {feature} disconnect isolated empty store', auth + ['disconnect', feature])
        self.experiment_checks(experiment)
        self.run('product tests', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', PRODUCT / 'tests', '-q'], contains='OK')
        self.run('experiment tests', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', ROOT / 'experiments/code/tests', '-q'], contains='OK')

    def workflow_checks(self, workflow):
        base = workflow + ['--store', self.temp / 'workflow.sqlite3']
        self.run('workflow mailbox', base + ['mailbox'])
        fetched = json.loads(self.run('workflow fetch m1', base + ['fetch', 'm1']))['result']
        rid = fetched['id']
        analyzed = json.loads(self.run('workflow analyze', base + ['analyze', rid]))['result']
        proposal = analyzed['proposals'][0]
        pid = proposal['id']
        self.run('workflow show', base + ['show', rid])
        self.run('workflow accept', base + ['review', rid, pid, '--state', 'accepted'])
        start = date.fromisoformat(proposal['deadline'])
        fields = self.temp / 'fields.json'
        fields.write_text(json.dumps({'title': proposal['text'], 'description': 'Offline command check.', 'start': start.isoformat(),
                          'end': (start + timedelta(days=1)).isoformat(), 'timezone': 'Asia/Singapore',
                          'calendar_id': 'demo@example.com', 'all_day': True}), encoding='utf-8')
        drafted = json.loads(self.run('workflow calendar draft', base + ['draft', rid, pid, '--fields', fields]))['result']
        revision = drafted['proposals'][0]['draft']['revision']
        self.run('workflow rejects stale confirmation', base + ['confirm', rid, pid, '--revision', 'stale'], expected=1)
        self.run('workflow confirm exact revision', base + ['confirm', rid, pid, '--revision', revision])
        export = self.temp / 'deadline.ics'
        self.run('workflow export ICS', base + ['export', rid, pid, '--output', export])
        assert b'BEGIN:VCALENDAR' in export.read_bytes()
        self.run('workflow refuses ICS overwrite', base + ['export', rid, pid, '--output', export], expected=1)
        self.run('workflow simulated write', base + ['simulate-write', rid, pid])
        self.run('workflow idempotent simulated write', base + ['simulate-write', rid, pid])
        self.run('workflow list', base + ['list'])
        self.run('workflow tasks', base + ['tasks'])
        self.run('workflow local JSON import', base + ['import', PRODUCT / 'examples/sample_email.json'])
        self.run('workflow local EML import', base + ['import', PRODUCT / 'evaluation/archive/fixtures_v2_1/A04.eml', '--recipient', 'alex@example.com'])
        self.run('workflow standalone demo', workflow + ['demo', '--output-dir', self.temp / 'long-demo'])

    def model_checks(self, short):
        checks = self

        class LocalChat(BaseHTTPRequestHandler):
            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                checks.calls += 1
                prompt = request['messages'][-1]['content']
                spans = list(re.finditer(r'SOURCE ([\w:-]+)[^\n]*:\n([^\n]+)', prompt))
                span = next((m for m in reversed(spans) if m[1] == 'body'), spans[-1] if spans else None)
                quotes = [{'source_id': span[1], 'quote': span[2]}] if span else []
                content = {'status': 'needs_review', 'actions': [], 'reason': 'Scripted local command check; human review required.',
                           'evidence': quotes, 'explanation': {'text': 'Scripted local command check.', 'evidence': quotes}}
                if 'task_text' in request['messages'][0]['content']:
                    content = {'status': 'needs_review', 'task_text': None, 'deadline': None, 'evidence': quotes,
                               'review_reason': 'Scripted local command check.'}
                body = json.dumps({'model': 'local-scripted', 'choices': [{'message': {'content': json.dumps(content)}}],
                                   'usage': {'prompt_tokens': 100, 'completion_tokens': 50}}).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), LocalChat)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        env = {**self.env, 'ACTIONMAIL_MODEL': 'local-scripted', 'OPENROUTER_API_KEY': 'local-test-placeholder',
               'ACTIONMAIL_API_URL': f'http://127.0.0.1:{server.server_port}/chat/completions'}
        try:
            sample = PRODUCT / 'examples/sample_email.json'
            self.run('analyze cancel before API', short + ['analyze', sample, '--schema', 'v2'], stdin='n\n', env=env, contains='Cancelled')
            assert self.calls == 0
            self.run('analyze missing confirmation stops', short + ['analyze', sample], expected=1, env=env, contains='confirmation input is unavailable')
            assert self.calls == 0
            self.run('analyze v2 local HTTP response', short + ['analyze', sample, '--schema', 'v2', '--external-mode', 'snapshots'], stdin='y\nn\n', env=env, contains='needs_review')
            self.run('legacy single-email local HTTP response', short + [sample], stdin='y\nn\n', env=env, contains='needs_review')
            pricing = ['--input-price-per-million', '1', '--output-price-per-million', '2']
            before = self.calls
            self.run('eval estimate local declared prices', short + ['eval', '--estimate', '--limit', '1', *pricing], env=env, contains='Expected batch cost')
            self.run('eval cancel before API', short + ['eval', '--limit', '1', *pricing], env=env, stdin='n\n', contains='Cancelled before model calls')
            assert self.calls == before
            self.run('eval local HTTP one case', short + ['eval', '--limit', '1', '--yes', '--output-dir', self.temp / 'local-eval', *pricing], env=env, contains='Saved 1 case result(s)')
            row = json.loads((self.temp / 'local-eval/cases.jsonl').read_text())
            assert not row['error'] and row['prediction'], row
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def experiment_checks(self, command):
        bundle = ROOT / 'experiments/data/frozen-core'
        self.run('experiment plan saved bundle', command + ['plan', '--bundle', bundle, '--config', ROOT / 'experiments/code/configs/model-benchmark.json'])
        self.run('experiment inspect original S02', command + ['inspect', '--bundle', bundle, '--case-id', 'S02'])
        prepared = self.temp / 'prepared'
        self.run('experiment prepare explicit source', command + ['prepare', '--source', PRODUCT, '--output', prepared], contains='60 self-contained cases')
        self.run('experiment smoke bundle', command + ['smoke-bundle', '--bundle', prepared])
        smoke = self.temp / 'prepared-smoke'
        run = self.temp / 'scripted-experiment'
        self.run('experiment run scripted three cases', command + ['run', '--bundle', smoke, '--arm', 'prompt_only', '--scripted', '--output', run], contains='Completed 3 analyses')
        self.run('experiment score temporary results', command + ['score', '--run', run])
        self.run('experiment review-score pending worksheet', command + ['review-score', '--run', run])
        self.run('experiment mechanism offline', command + ['mechanism', '--bundle', prepared, '--output', self.temp / 'mechanism'])
        benchmark = ROOT / 'experiments/results/model-benchmark'
        self.run('experiment screen saved benchmark', command + ['screen', '--run', benchmark])
        self.run('experiment stage2 config temporary output', command + ['stage2-config', '--benchmark-run', benchmark,
                 '--model', 'm01', '--model', 'm02', '--reason', 'Offline CLI check only.', '--output', self.temp / 'stage2.json'])
        self.run('experiment refuses unapproved paid run', command + ['run', '--bundle', bundle, '--arm', 'full', '--output', self.temp / 'unapproved'], expected=1, contains='--approve-paid')
        self.run('experiment reconcile missing credentials stops', command + ['reconcile', '--run', run], expected=1, contains='OPENROUTER_API_KEY required')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, help='Write command outcomes as JSON outside sealed experiment results')
    args = parser.parse_args()
    if args.report and args.report.resolve().is_relative_to((ROOT / 'experiments/results').resolve()):
        parser.error('Do not overwrite sealed experiment results')
    with tempfile.TemporaryDirectory(prefix='actionmail-command-checks-') as temporary:
        checks = Checks(temporary)
        try:
            checks.execute()
            code = 0
        except Exception as exc:
            print(f'Command checks stopped: {exc}', file=sys.stderr)
            code = 1
        report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                  'python': sys.version.split()[0], 'scope': 'Offline engineering command checks; not model accuracy or live Google integration',
                  'real_model_calls': 0, 'real_google_requests': 0, 'local_scripted_http_calls': checks.calls,
                  'passed': sum(row['passed'] for row in checks.results), 'total': len(checks.results),
                  'complete': code == 0, 'checks': checks.results}
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(f"Command checks: {report['passed']}/{report['total']} passed; complete={report['complete']}")
        return code


if __name__ == '__main__':
    raise SystemExit(main())
