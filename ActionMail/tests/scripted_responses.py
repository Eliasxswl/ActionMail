"""Supply explanation fields for legacy scripted fixtures, without modifying gold."""
import json
import re


def explained(value, prompt):
    value = json.loads(json.dumps(value))
    spans = list(re.finditer(r'SOURCE ([\w:-]+)[^\n]*:\n([^\n]+)', prompt))
    span = next((m for m in reversed(spans) if m[1] == 'body'), spans[-1] if spans else None)
    quotes = [{'source_id': span[1], 'quote': span[2]}] if span else []
    if 'actions' in value and 'explanation' not in value:
        action_quotes = [e for a in value['actions'] for e in (a['evidence'] if isinstance(a['evidence'], list) else [a['evidence']])]
        value['explanation'] = {'text': 'Offline scripted decision for the supplied target and source.', 'evidence': action_quotes or quotes}
    if 'sources' in value:
        for item in value['sources']:
            item.setdefault('evidence', quotes)
    return value
