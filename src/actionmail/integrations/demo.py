"""Authored Google-shaped fixtures and scripted model replies, never accuracy data."""
import copy
import json
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, unquote

from actionmail.integrations.google import ProviderError
from actionmail.reasoning.model_client import ModelReply


def fixtures():
    return json.loads(files('actionmail.integrations').joinpath('demo_mail.json').read_text(encoding='utf-8'))


class DemoGoogleTransport:
    def __init__(self, events_path=None):
        self.data = fixtures()
        self.events = {}
        self.events_path = Path(events_path) if events_path else None
        if self.events_path and self.events_path.exists():
            self.events = {(item['calendar_id'], item['event']['id']): item['event']
                           for item in json.loads(self.events_path.read_text(encoding='utf-8'))}
        self.calls = []

    def request(self, method, url, body=None):
        self.calls.append((method, url, copy.deepcopy(body)))
        parts = urlsplit(url)
        path = unquote(parts.path)
        if path.endswith('/profile'):
            return {'emailAddress': self.data['account'], 'messagesTotal': len(self.data['messages']), 'threadsTotal': 3}
        if path.endswith('/messages'):
            return {'messages': [{'id': m['id'], 'threadId': m['threadId']} for m in self.data['messages']], 'resultSizeEstimate': 3}
        if '/attachments/' in path:
            key = path.rsplit('/', 1)[-1]
            return copy.deepcopy(self.data['attachments'][key])
        if '/messages/' in path:
            message_id = path.rsplit('/', 1)[-1]
            for m in self.data['messages'] + self.data['history']:
                if m['id'] == message_id:
                    result = copy.deepcopy(m)
                    if parse_qs(parts.query).get('format') == ['metadata']:
                        result['payload'] = {'headers': result['payload']['headers']}
                    return result
        if '/threads/' in path:
            thread_id = path.rsplit('/', 1)[-1]
            return {'id': thread_id, 'messages': copy.deepcopy([m for m in self.data['messages'] + self.data['history'] if m['threadId'] == thread_id])}
        if path.endswith('/calendarList'):
            return {'items': [{'id': 'demo@example.com', 'summary': 'Demo calendar', 'timeZone': 'Asia/Singapore', 'accessRole': 'owner', 'primary': True}]}
        if '/events' in path:
            calendar_id = path.split('/calendars/', 1)[1].split('/events')[0]
            if method == 'POST':
                key = calendar_id, body['id']
                if key in self.events:
                    raise ProviderError(409, 'Event ID already exists')
                self.events[key] = copy.deepcopy(body)
                if self.events_path:
                    self.events_path.parent.mkdir(parents=True, exist_ok=True)
                    temporary = self.events_path.with_suffix('.tmp')
                    temporary.write_text(json.dumps([{'calendar_id': k[0], 'event': v} for k, v in self.events.items()]), encoding='utf-8')
                    temporary.replace(self.events_path)
                return copy.deepcopy(body)
            key = calendar_id, path.rsplit('/', 1)[-1]
            if key in self.events:
                return copy.deepcopy(self.events[key])
        raise ProviderError(404, 'Synthetic resource not found')


class DemoModel:
    """Only replay known authored bodies. Unknown imports remain needs_review."""
    simulated = True

    def complete(self, system_prompt, user_prompt):
        data = fixtures()
        scenario = next((s for s in data['scripts'] if s['body'] in user_prompt), None)
        if scenario is None:
            value = {'status': 'needs_review', 'actions': [],
                     'reason': 'Offline simulation has no scripted response for this imported message. Enable a real model later to analyze it.',
                     'evidence': []}
            # The original core still enforces evidence; quote a supplied original span.
            marker = 'SOURCE body'
            if marker in user_prompt:
                tail = user_prompt.split(marker)[-1].split('\n', 1)[-1]
                quote = next((line for line in tail.splitlines() if line.strip()), '')
                if quote:
                    value['evidence'] = [{'source_id': 'body', 'quote': quote}]
        elif '"sources"' in system_prompt:
            value = scenario['plan']
        else:
            value = scenario['decision']
        return ModelReply(json.dumps(value), 'offline-scripted-demo', 0, 0, 0)
