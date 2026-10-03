"""Offline CLI for the persistent application; no account or model API required."""
import argparse
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from actionmail.application.service import ApplicationService
from actionmail.application.store import Store
from actionmail.ingestion.eml import load_eml_bytes
from actionmail.ingestion.fixtures import load_json_email
from actionmail.integrations.auth import private_home
from actionmail.integrations.calendar import GoogleCalendarAdapter
from actionmail.integrations.demo import DemoGoogleTransport, DemoModel
from actionmail.integrations.google import ProviderError
from actionmail.integrations.mail import GmailAdapter, MailRecord


MODE = 'offline-scripted-engineering-demo'


def record_view(record):
    """Keep original text and traces, but omit base64 attachment bytes from output."""
    value = dict(record)
    value['email'] = dict(record['email'])
    value['email']['external_sources'] = [
        {key: item for key, item in source.items() if key != 'content'}
        for source in record['email']['external_sources']]
    return value


def runtime(path):
    transport = DemoGoogleTransport(path.with_suffix('.demo-events.json'))
    calendar = GoogleCalendarAdapter(transport)
    calendar.simulated = True
    calendar.account = 'demo@example.com'
    return ApplicationService(Store(path), DemoModel(), calendar), GmailAdapter(transport), transport


def parser():
    result = argparse.ArgumentParser(
        prog='actionmail-workflow',
        description='Persistent offline workflow. Scripted replies are not AI accuracy measurements.')
    result.add_argument('--store', type=Path, help='Private SQLite store; default is a separate CLI demo store')
    commands = result.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('demo', help='Run three supplied scenarios and save inspectable artifacts')
    demo.add_argument('--output-dir', type=Path, required=True, help='New directory; existing paths are refused')
    commands.add_parser('mailbox', help='List synthetic Gmail message IDs')
    fetch = commands.add_parser('fetch', help='Import one synthetic Gmail message')
    fetch.add_argument('message_id')
    imp = commands.add_parser('import', help='Import a local JSON or EML; unknown bodies receive scripted review')
    imp.add_argument('input', type=Path)
    imp.add_argument('--recipient', help='Required for EML')
    commands.add_parser('list', help='List stored record IDs, subjects and states')
    commands.add_parser('tasks', help='List accepted tasks')
    for name in ('show', 'analyze'):
        command = commands.add_parser(name, help='Show saved sources/traces' if name == 'show' else 'Run scripted analysis')
        command.add_argument('record_id')
        if name == 'analyze':
            command.add_argument('--force', action='store_true')
    review = commands.add_parser('review', help='Explicitly accept, edit or reject a proposal')
    review.add_argument('record_id')
    review.add_argument('proposal_id')
    review.add_argument('--state', choices=('accepted', 'rejected'), required=True)
    review.add_argument('--text')
    review.add_argument('--deadline', help='ISO date/time, or null to clear; omission retains existing value')
    draft = commands.add_parser('draft', help='Save calendar preview fields from JSON')
    draft.add_argument('record_id')
    draft.add_argument('proposal_id')
    draft.add_argument('--fields', type=Path, required=True)
    for name in ('confirm', 'export', 'simulate-write'):
        command = commands.add_parser(name)
        command.add_argument('record_id')
        command.add_argument('proposal_id')
        if name == 'confirm':
            command.add_argument('--revision', required=True, help='Exact revision shown by draft/show')
        elif name == 'export':
            command.add_argument('--output', type=Path, required=True, help='New ICS file')
    return result


def demo(output):
    output.mkdir(parents=True, exist_ok=False)
    service, mail, transport = runtime(output / 'workflow.sqlite3')
    records = [service.analyze(service.import_mail(mail.fetch(item['id']))['id'])
               for item in mail.list_messages()['messages']]
    if any(record['state'] == 'failed' for record in records):
        raise ValueError('Scripted analysis failed; inspect the saved store')
    record = next(record for record in records if record['message_id'] == 'm1')
    proposal = record['proposals'][0]
    record = service.review(record['id'], proposal['id'], 'accepted', proposal['text'], proposal['deadline'])
    start = date.fromisoformat(proposal['deadline'])
    fields = {'title': proposal['text'], 'description': 'Authored demonstration email; synthetic calendar only.',
              'start': start.isoformat(), 'end': (start + timedelta(days=1)).isoformat(),
              'timezone': 'Asia/Singapore', 'calendar_id': 'demo@example.com', 'all_day': True}
    record = service.save_draft(record['id'], proposal['id'], fields)
    revision = record['proposals'][0]['draft']['revision']
    service.confirm(record['id'], proposal['id'], revision)
    (output / 'deadline.ics').write_bytes(service.ics(record['id'], proposal['id']))
    service.write(record['id'], proposal['id'])
    service.write(record['id'], proposal['id'])
    records = [record_view(service.store.get(record['id'])) for record in records]
    summary = {'mode': MODE, 'real_model_calls': 0, 'real_provider_requests': 0,
               'scenarios': [{'record_id': record['id'], 'message_id': record['message_id'],
                              'subject': record['email']['subject'],
                              'status': record['analysis']['decision']['status'],
                              'action_count': len(record['proposals'])} for record in records],
               'accepted_tasks': len(service.tasks()), 'simulated_events': len(transport.events),
               'simulated_write_requests': sum(method == 'POST' for method, _, _ in transport.calls),
               'artifacts': ['records.json', 'summary.json', 'deadline.ics', 'workflow.sqlite3',
                             'workflow.demo-events.json'],
               'boundary': 'Authored inputs and scripted model replies; not model accuracy or live integration.'}
    for filename, value in (('records.json', records), ('summary.json', summary)):
        (output / filename).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return {**summary, 'output_dir': str(output.resolve())}


def execute(args):
    if args.command == 'demo':
        if args.store:
            raise ValueError('demo uses a fresh store inside --output-dir; omit --store')
        return demo(args.output_dir)
    service, mail, _ = runtime(args.store or private_home() / 'cli-demo.sqlite3')
    if args.command == 'mailbox':
        return mail.list_messages()
    if args.command == 'fetch':
        return record_view(service.import_mail(mail.fetch(args.message_id)))
    if args.command == 'import':
        raw = args.input.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if args.input.suffix.lower() == '.eml':
            if not args.recipient or '@' not in args.recipient:
                raise ValueError('--recipient is required for EML')
            email = load_eml_bytes(raw, args.recipient, case_id=digest)
        elif args.input.suffix.lower() == '.json':
            email = load_json_email(args.input)
        else:
            raise ValueError('Input must be JSON or EML')
        return record_view(service.import_mail(MailRecord('local', email.target_recipient, digest, '', '', email)))
    if args.command == 'list':
        return [{'record_id': record['id'], 'subject': record['email']['subject'], 'state': record['state']}
                for record in service.store.all()]
    if args.command == 'tasks':
        return service.tasks()
    if args.command == 'show':
        return record_view(service.store.get(args.record_id))
    if args.command == 'analyze':
        record = service.analyze(args.record_id, force=args.force)
        if record['state'] == 'failed':
            raise ValueError(record['error'] or 'Analysis failed; inspect show for saved trace')
    elif args.command == 'review':
        current = service.store.get(args.record_id)
        proposal = service._proposal(current, args.proposal_id)
        deadline = proposal['deadline'] if args.deadline is None else (
            None if args.deadline.lower() == 'null' else args.deadline)
        record = service.review(args.record_id, args.proposal_id, args.state,
                                proposal['text'] if args.text is None else args.text, deadline)
    elif args.command == 'draft':
        fields = json.loads(args.fields.read_text(encoding='utf-8-sig'))
        if not isinstance(fields, dict):
            raise ValueError('Draft fields must be a JSON object')
        record = service.save_draft(args.record_id, args.proposal_id, fields)
    elif args.command == 'confirm':
        record = service.confirm(args.record_id, args.proposal_id, args.revision)
    elif args.command == 'export':
        # Refuse overwrite before recording an export in application history.
        with args.output.open('xb') as handle:
            try:
                handle.write(service.ics(args.record_id, args.proposal_id))
            except Exception:
                handle.close()
                args.output.unlink()
                raise
        return {'ics': str(args.output.resolve())}
    elif args.command == 'simulate-write':
        record = service.write(args.record_id, args.proposal_id)
        draft = service._proposal(record, args.proposal_id)['draft']
        if draft['state'] != 'written':
            raise ValueError(draft['error'] or 'Simulated write incomplete; inspect show')
    return record_view(record)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        value = execute(args)
        print(json.dumps({'mode': MODE, 'result': value}, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, ProviderError) as exc:
        print(json.dumps({'mode': MODE, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
