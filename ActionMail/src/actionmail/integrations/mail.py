"""Gmail v1 read-only adapter using full MIME payloads and internalDate anchors."""
import base64
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from email.message import EmailMessage
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

from actionmail.domain.email import SourceText
from actionmail.ingestion.eml import load_eml_bytes

BASE = 'https://gmail.googleapis.com/gmail/v1/users/me/'
MAX_MESSAGE_BYTES = 20 * 1024 * 1024


def decode_data(value):
    if len(value) > MAX_MESSAGE_BYTES * 4 // 3 + 4:
        raise ValueError('Mail content exceeds the byte limit')
    return base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True)


@dataclass(frozen=True)
class MailRecord:
    provider: str
    account: str
    message_id: str
    thread_id: str
    source_url: str
    email: object


class GmailAdapter:
    def __init__(self, transport, timezone_name='Asia/Singapore'):
        self.transport = transport
        self.timezone = ZoneInfo(timezone_name)

    def profile(self):
        return self.transport.request('GET', BASE + 'profile')['emailAddress']

    def list_messages(self, *, limit=20, page_token=None):
        if not 1 <= limit <= 50:
            raise ValueError('Message limit must be between 1 and 50')
        params = {'maxResults': limit, 'labelIds': 'INBOX'}
        if page_token:
            params['pageToken'] = page_token
        listing = self.transport.request('GET', BASE + 'messages?' + urlencode(params))
        summaries = []
        for item in listing.get('messages', [])[:limit]:
            message = self.transport.request('GET', BASE + 'messages/' + quote(item['id'], safe='') +
                                             '?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=To')
            headers = {h['name'].lower(): h['value'] for h in message.get('payload', {}).get('headers', [])}
            summaries.append({'id': message['id'], 'thread_id': message['threadId'],
                              'subject': headers.get('subject', ''), 'sender': headers.get('from', ''),
                              'received_at': self._received(message).isoformat()})
        return {'messages': summaries, 'next_page_token': listing.get('nextPageToken')}

    def _received(self, message):
        return datetime.fromtimestamp(int(message['internalDate']) / 1000, timezone.utc).astimezone(self.timezone)

    def _package(self, message, account):
        consumed = 0
        count = 0

        def mime(part):
            nonlocal consumed, count
            count += 1
            if count > 100:
                raise ValueError('Too many MIME parts')
            output = EmailMessage()
            for header in part.get('headers', []):
                output[header['name']] = header['value']
            if not output.get('Content-Type'):
                output['Content-Type'] = part.get('mimeType', 'application/octet-stream')
            if part.get('filename') and not output.get('Content-Disposition'):
                output.add_header('Content-Disposition', 'attachment', filename=part['filename'])
            if part.get('parts'):
                output.set_payload([mime(child) for child in part['parts']])
            else:
                body = part.get('body', {})
                if int(body.get('size', 0)) > MAX_MESSAGE_BYTES:
                    raise ValueError('MIME part exceeds the byte limit')
                if body.get('attachmentId'):
                    body = self.transport.request('GET', BASE + 'messages/' + quote(message['id'], safe='') +
                                                  '/attachments/' + quote(body['attachmentId'], safe=''))
                data = decode_data(body.get('data', ''))
                consumed += len(data)
                if consumed > MAX_MESSAGE_BYTES:
                    raise ValueError('Message exceeds the byte limit')
                if output.get('Content-Transfer-Encoding'):
                    del output['Content-Transfer-Encoding']
                output['Content-Transfer-Encoding'] = 'base64'
                output.set_payload(base64.b64encode(data).decode('ascii'))
            return output

        return load_eml_bytes(mime(message['payload']).as_bytes(), account,
                              case_id=message['id'], received_at=self._received(message))

    def fetch(self, message_id):
        account = self.profile()
        selected = self.transport.request('GET', BASE + 'messages/' + quote(message_id, safe='') + '?format=full')
        if selected['id'] != message_id:
            raise ValueError('Provider returned the wrong message')
        thread = self.transport.request('GET', BASE + 'threads/' + quote(selected['threadId'], safe='') + '?format=full')
        messages = thread.get('messages', [])
        if len(messages) > 50:
            raise ValueError('Thread exceeds 50 messages; import a bounded thread instead')
        # A selected historical message remains the current boundary. Later replies are excluded.
        ordered = sorted(messages, key=lambda m: (int(m['internalDate']), m['id']))
        indices = [i for i, m in enumerate(ordered) if m['id'] == message_id]
        if not indices:
            raise ValueError('Selected message missing from its thread')
        package = self._package(selected, account)
        historical, external = [], list(package.external_sources)
        total_bytes = len(package.body.encode()) + sum(len(s.content or b'') for s in external)
        for index, message in enumerate(ordered[:indices[0]], start=1):
            previous = self._package(message, account)
            total_bytes += len(previous.body.encode()) + sum(len(s.content or b'') for s in previous.external_sources)
            if total_bytes > MAX_MESSAGE_BYTES:
                raise ValueError('Combined thread exceeds the byte limit')
            sid = f'thread:{index}'
            historical.append(SourceText(sid, previous.body, previous.sender, ', '.join(previous.to_recipients),
                                         ', '.join(previous.cc_recipients), previous.subject))
            external.extend(replace(s, source_id=sid + ':' + s.source_id) for s in previous.external_sources)
        package = replace(package, thread=tuple(historical), external_sources=tuple(external),
                          unread_sources=tuple(s.name for s in external))
        return MailRecord('gmail', account, selected['id'], selected['threadId'],
                          'https://mail.google.com/mail/u/' + quote(account, safe='') + '/#all/' +
                          quote(selected['threadId'], safe=''), package)
