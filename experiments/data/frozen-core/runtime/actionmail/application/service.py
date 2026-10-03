"""Explicit analyze, review, draft, confirm and write operations on the v2 core."""
import hashlib
import json
import threading
import uuid
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone

from actionmail.application.store import encode_email, decode_email
from actionmail.integrations.calendar import validate_draft, export_ics
from actionmail.integrations.google import UnknownWrite, ProviderError
from actionmail.reasoning.api_client import ModelCallError
from actionmail.workflow.multi_pipeline import process_email_multi_with_external


def now():
    return datetime.now(timezone.utc).isoformat()


class CappedModel:
    def __init__(self, model, maximum=80):
        self.model, self.remaining = model, maximum

    def complete(self, system_prompt, user_prompt):
        if self.remaining <= 0:
            raise ModelCallError('Application model-call limit exceeded')
        self.remaining -= 1
        return self.model.complete(system_prompt, user_prompt)


class ApplicationService:
    def __init__(self, store, model, calendar=None):
        self.store, self.model, self.calendar = store, model, calendar
        self.lock = threading.RLock()
        # Recover persisted in-flight states without blind repeats after a crash.
        for record in store.all():
            changed = False
            if record['state'] == 'analyzing':
                record.update(state='failed', error='Analysis interrupted; request a new analysis explicitly')
                changed = True
            for proposal in record['proposals']:
                draft = proposal.get('draft')
                if draft and draft['state'] == 'writing':
                    draft['state'] = 'unknown'
                    changed = True
            if changed:
                store.save(record)

    def import_mail(self, mail):
        with self.lock:
            package = encode_email(mail.email)
            digest = hashlib.sha256(json.dumps(package, sort_keys=True).encode()).hexdigest()
            identity = json.dumps([mail.provider, mail.account, mail.message_id])
            previous = self.store.find(identity)
            if previous and previous['content_hash'] == digest:
                return previous
            if previous and any((p.get('draft') or {}).get('state') in {'writing', 'unknown'} for p in previous['proposals']):
                raise ValueError('Resolve the previous calendar outcome before refreshing changed mail')
            record = {'id': previous['id'] if previous else uuid.uuid4().hex, 'identity': identity,
                      'provider': mail.provider, 'account': mail.account, 'message_id': mail.message_id,
                      'thread_id': mail.thread_id, 'source_url': mail.source_url, 'email': package,
                      'content_hash': digest, 'state': 'ready', 'analysis': None, 'proposals': [],
                      'history': previous['history'] if previous else [], 'error': None}
            if previous:
                record['history'].append({'at': now(), 'operation': 'content_changed',
                                          'previous_analysis': previous['analysis'], 'previous_proposals': previous['proposals']})
            self.store.save(record)
            return record

    def analyze(self, record_id, *, force=False):
        with self.lock:
            record = self.store.get(record_id)
            if record['analysis'] and not force:
                return record
            if record['proposals'] and force:
                raise ValueError('Reviewed proposals exist; retain them rather than silently replacing them')
            record.update(state='analyzing', error=None)
            self.store.save(record)
            try:
                run = process_email_multi_with_external(decode_email(record['email']), CappedModel(self.model))
                record['analysis'] = asdict(run)
                record['proposals'] = [{'id': uuid.uuid4().hex, 'state': 'proposed', 'text': action.text,
                                        'deadline': action.deadline, 'evidence': [asdict(e) for e in action.evidence],
                                        'draft': None} for action in run.decision.actions]
                record.update(state='failed' if run.model_error else 'analyzed', error=run.model_error)
            except Exception:
                record.update(state='failed', error='Analysis failed; no task was accepted')
                self.store.save(record)
                raise
            record['history'].append({'at': now(), 'operation': 'analyze', 'state': record['state']})
            self.store.save(record)
            return record

    def _proposal(self, record, proposal_id):
        for item in record['proposals']:
            if item['id'] == proposal_id:
                return item
        raise KeyError('Proposal not found')

    def review(self, record_id, proposal_id, state, text, deadline):
        with self.lock:
            record = self.store.get(record_id)
            proposal = self._proposal(record, proposal_id)
            if state not in {'accepted', 'rejected'} or not isinstance(text, str) or not text.strip() or len(text) > 2000:
                raise ValueError('Choose accepted or rejected and provide task text')
            if deadline is not None:
                if not isinstance(deadline, str):
                    raise ValueError('Deadline must be an ISO date/time or null')
                if len(deadline) == 10:
                    date.fromisoformat(deadline)
                else:
                    parsed = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                    if parsed.tzinfo is None:
                        raise ValueError('Deadline time requires a UTC offset')
            if (proposal.get('draft') or {}).get('state') in {'writing', 'written', 'unknown'}:
                raise ValueError('Resolve the calendar outcome before changing the task')
            proposal.update(state=state, text=text.strip(), deadline=deadline, draft=None)
            record['state'] = 'reviewed'
            record['history'].append({'at': now(), 'operation': 'review', 'proposal_id': proposal_id,
                                      'state': state, 'text': text.strip(), 'deadline': deadline})
            self.store.save(record)
            return record

    def save_draft(self, record_id, proposal_id, fields):
        with self.lock:
            record = self.store.get(record_id)
            proposal = self._proposal(record, proposal_id)
            if proposal['state'] != 'accepted':
                raise ValueError('Accept the task before drafting a calendar item')
            old = proposal.get('draft')
            if old and old['state'] in {'writing', 'written', 'unknown'}:
                raise ValueError('Resolve the existing calendar operation before editing')
            fields = validate_draft(fields)
            proposal['draft'] = {'fields': fields, 'revision': uuid.uuid4().hex, 'operation_key': uuid.uuid4().hex,
                                 'state': 'draft', 'provider_id': None, 'error': None}
            record['history'].append({'at': now(), 'operation': 'draft', 'proposal_id': proposal_id})
            self.store.save(record)
            return record

    def confirm(self, record_id, proposal_id, revision):
        with self.lock:
            record = self.store.get(record_id)
            proposal = self._proposal(record, proposal_id)
            draft = proposal.get('draft')
            if proposal['state'] != 'accepted' or not draft or draft['revision'] != revision:
                raise ValueError('Draft changed; review the current fields before confirming')
            if draft['state'] in {'unknown', 'writing'}:
                raise ValueError('Reconcile the unknown outcome before retrying')
            if draft['state'] == 'written':
                return record
            draft['state'] = 'confirmed'
            record['history'].append({'at': now(), 'operation': 'confirm', 'proposal_id': proposal_id,
                                      'revision': revision, 'fields': draft['fields']})
            self.store.save(record)
            return record

    def cancel_draft(self, record_id, proposal_id):
        with self.lock:
            record = self.store.get(record_id)
            proposal = self._proposal(record, proposal_id)
            draft = proposal.get('draft')
            if draft and draft['state'] in {'writing', 'written', 'unknown'}:
                raise ValueError('Resolve the calendar outcome before cancelling locally')
            proposal['draft'] = None
            record['history'].append({'at': now(), 'operation': 'cancel_draft', 'proposal_id': proposal_id})
            self.store.save(record)
            return record

    def write(self, record_id, proposal_id):
        with self.lock:
            record = self.store.get(record_id)
            proposal = self._proposal(record, proposal_id)
            draft = proposal.get('draft')
            if not draft or proposal['state'] != 'accepted':
                raise ValueError('An accepted task and confirmed draft are required')
            if draft['state'] == 'written':
                return record
            if draft['state'] != 'confirmed':
                raise ValueError('Explicit final confirmation is required before writing')
            if self.calendar is None:
                raise ValueError('Calendar API is disabled; ICS export is available')
            draft['state'] = 'writing'
            self.store.save(record)
            try:
                event = self.calendar.create(draft['fields'], draft['operation_key'])
                draft.update(state='written', provider_id=event['id'], error=None,
                             simulated=bool(self.calendar.simulated))
            except ProviderError as exc:
                draft.update(state='failed', error=str(exc))
            except Exception:
                draft.update(state='unknown', error='Write outcome unknown; reconcile before retry')
            record['history'].append({'at': now(), 'operation': 'write', 'proposal_id': proposal_id,
                                      'state': draft['state'], 'provider_id': draft['provider_id']})
            self.store.save(record)
            return record

    def reconcile(self, record_id, proposal_id):
        with self.lock:
            record = self.store.get(record_id)
            draft = self._proposal(record, proposal_id).get('draft')
            if not self.calendar or not draft or draft['state'] != 'unknown':
                raise ValueError('An unknown calendar write is required for reconciliation')
            event = self.calendar.get(draft['fields']['calendar_id'], draft['operation_key'])
            if event:
                draft.update(state='written', provider_id=event['id'], error=None,
                             simulated=bool(self.calendar.simulated))
            else:
                # A 404 may be transient. Keep the operation locked and do not auto-retry.
                draft['error'] = 'Event not yet found; reconcile later or resolve manually. No write was repeated.'
            record['history'].append({'at': now(), 'operation': 'reconcile', 'proposal_id': proposal_id,
                                      'state': draft['state'], 'provider_id': draft['provider_id']})
            self.store.save(record)
            return record

    def ics(self, record_id, proposal_id):
        with self.lock:
            record = self.store.get(record_id)
            proposal = self._proposal(record, proposal_id)
            draft = proposal.get('draft')
            if proposal['state'] != 'accepted' or not draft or draft['state'] != 'confirmed':
                raise ValueError('Confirm the final calendar draft before export')
            record['history'].append({'at': now(), 'operation': 'ics_export', 'proposal_id': proposal_id,
                                      'revision': draft['revision']})
            self.store.save(record)
            return export_ics(draft['fields'], draft['operation_key'])

    def tasks(self):
        with self.lock:
            return [{'message_id': record['id'], 'subject': record['email']['subject'],
                     'account': record['account'], 'source_url': record['source_url'], **proposal}
                    for record in self.store.all() for proposal in record['proposals'] if proposal['state'] == 'accepted']
