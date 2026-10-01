"""Google Calendar v3 payloads and RFC 5545 export, without model-owned effects."""
import hashlib
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from actionmail.integrations.google import ProviderError, UnknownWrite

BASE = 'https://www.googleapis.com/calendar/v3/'


def validate_draft(value):
    result = {key: value.get(key) for key in ('title', 'description', 'start', 'end', 'timezone', 'calendar_id', 'all_day')}
    for key in ('title', 'start', 'end', 'timezone', 'calendar_id'):
        if not isinstance(result[key], str) or not result[key].strip():
            raise ValueError(f'{key} is required')
    if not isinstance(result['all_day'], bool):
        raise ValueError('all_day must be true or false')
    if not isinstance(result['description'], str):
        raise ValueError('description must be text')
    if any(len(result[key]) > maximum for key, maximum in
           (('title', 500), ('description', 5000), ('calendar_id', 500), ('timezone', 100))):
        raise ValueError('Calendar field exceeds the length limit')
    try:
        zone = ZoneInfo(result['timezone'])
    except ZoneInfoNotFoundError as exc:
        raise ValueError('Use a valid IANA timezone, such as Asia/Singapore') from exc
    if result['all_day']:
        start, end = date.fromisoformat(result['start']), date.fromisoformat(result['end'])
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', result['start']) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', result['end']):
            raise ValueError('All-day dates must use YYYY-MM-DD')
    else:
        start, end = (datetime.fromisoformat(result[key].replace('Z', '+00:00')) for key in ('start', 'end'))
        for item in (start, end):
            if item.tzinfo is None or item.utcoffset() is None:
                raise ValueError('Timed dates require an explicit UTC offset')
            if item.astimezone(zone).replace(tzinfo=None) != item.replace(tzinfo=None):
                raise ValueError('UTC offset does not match the selected timezone at this date')
    if end <= start:
        raise ValueError('End must follow start (all-day end is exclusive)')
    return result


def event_id(operation_key):
    # Hex is a subset of Google's required base32hex alphabet.
    return 'am' + hashlib.sha256(operation_key.encode()).hexdigest()


def event_payload(draft, operation_key):
    draft = validate_draft(draft)
    field = 'date' if draft['all_day'] else 'dateTime'
    return {'id': event_id(operation_key), 'summary': draft['title'], 'description': draft['description'],
            'start': {field: draft['start'], **({} if draft['all_day'] else {'timeZone': draft['timezone']})},
            'end': {field: draft['end'], **({} if draft['all_day'] else {'timeZone': draft['timezone']})},
            'transparency': 'transparent',
            'extendedProperties': {'private': {'actionmailOperation': operation_key}}}


class GoogleCalendarAdapter:
    simulated = False

    def __init__(self, transport):
        self.transport = transport

    def list_calendars(self):
        result = self.transport.request('GET', BASE + 'users/me/calendarList?minAccessRole=owner&maxResults=100')
        return [{'id': c['id'], 'title': c.get('summary', c['id']), 'timezone': c.get('timeZone'),
                 'primary': c.get('primary', False)}
                for c in result.get('items', [])]

    def validate_account(self, mail_account):
        primary = next((c for c in self.list_calendars() if c['primary']), None)
        if not primary or primary['id'].casefold() != mail_account.casefold():
            raise ValueError('Calendar authorization must use the same account as Gmail')
        self.account = primary['id']

    def get(self, calendar_id, operation_key):
        try:
            result = self.transport.request('GET', BASE + 'calendars/' + quote(calendar_id, safe='') +
                                             '/events/' + event_id(operation_key))
        except ProviderError as exc:
            if exc.status == 404:
                return None
            raise
        if result.get('status') == 'cancelled':
            raise ProviderError(409, 'Matching event was cancelled; resolve manually')
        if result.get('id') != event_id(operation_key) or result.get('extendedProperties', {}).get('private', {}).get('actionmailOperation') != operation_key:
            raise ProviderError(409, 'Event ID conflict; resolve manually')
        return result

    def create(self, draft, operation_key):
        try:
            result = self.transport.request('POST', BASE + 'calendars/' + quote(draft['calendar_id'], safe='') +
                                             '/events?sendUpdates=none', event_payload(draft, operation_key))
        except ProviderError as exc:
            if exc.status != 409:
                raise
            result = self.get(draft['calendar_id'], operation_key)
        if not result or result.get('id') != event_id(operation_key):
            raise UnknownWrite('No matching provider event ID; reconcile before retry')
        return result


def export_ics(draft, operation_key):
    draft = validate_draft(draft)

    def escape(text):
        return text.replace('\\', '\\\\').replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')

    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//ActionMail//Task Review//EN',
             'CALSCALE:GREGORIAN', 'BEGIN:VEVENT', 'UID:' + event_id(operation_key) + '@actionmail.local',
             'DTSTAMP:' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
             'SUMMARY:' + escape(draft['title']), 'DESCRIPTION:' + escape(draft['description']),
             'TRANSP:TRANSPARENT']
    for key, label in (('start', 'DTSTART'), ('end', 'DTEND')):
        if draft['all_day']:
            lines.append(label + ';VALUE=DATE:' + draft[key].replace('-', ''))
        else:
            instant = datetime.fromisoformat(draft[key].replace('Z', '+00:00')).astimezone(timezone.utc)
            lines.append(label + ':' + instant.strftime('%Y%m%dT%H%M%SZ'))
    lines.extend(['END:VEVENT', 'END:VCALENDAR'])
    folded = []
    for line in lines:
        current = ''
        for character in line:
            if len((current + character).encode('utf-8')) > 75:
                folded.append(current)
                current = ' '
            current += character
        folded.append(current)
    return ('\r\n'.join(folded) + '\r\n').encode('utf-8')
