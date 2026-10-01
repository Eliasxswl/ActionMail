"""Build decision context from source facts; do not infer unseen contents."""
import json
from dataclasses import asdict, replace
from actionmail.workflow.pipeline import _user_prompt


def decision_prompt(email, source_plan=(), *, include_text=True):
    package = email if include_text else replace(email, body='', thread=(), read_sources=(), unread_sources=())
    prompt = _user_prompt(package)
    read_ids = {s.source_id for s in email.read_sources}
    choices = {s.source_id: s for s in source_plan}
    states = []
    for source in email.external_sources:
        choice = choices.get(source.source_id)
        state = 'read' if source.source_id in read_ids else 'skipped_as_irrelevant' if choice and choice.relevance == 'irrelevant' else 'not_supplied'
        states.append({'source_id': source.source_id, 'kind': source.kind, 'name': source.name, 'state': state,
                       'reading_reason': choice.reason if choice else None,
                       'reading_evidence': [asdict(e) for e in choice.evidence] if choice else []})
    prompt += '\n\nEXTERNAL AVAILABILITY (system facts; reading reasons are interpretations, not new requests):\n' + json.dumps(states)
    prompt += '\nAn empty inventory means no external material was supplied, not that the email cannot refer to missing material. Only SOURCE blocks contain supplied original text. A skipped irrelevant source is not a failed read. If a current request depends on missing material, identify that dependency from original email quotes; never invent its name, contents or source ID.'
    return prompt
