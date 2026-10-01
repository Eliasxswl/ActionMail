"""Load the hash-bound active suite without changing either historical manifest."""
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from actionmail.evaluation.cases import load_cases
from actionmail.evaluation.challenge import load_challenge


def load_suite(registry: Path, mailex_root: Path, *, registry_data=None):
    suite = registry_data if registry_data is not None else json.loads(registry.read_text(encoding='utf-8'))
    cases = []
    for component in suite['components']:
        manifest = (registry.parent / component['manifest']).resolve()
        if not manifest.is_relative_to(registry.parent.resolve()):
            raise ValueError('Suite manifest escapes evaluation directory')
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != component['sha256']:
            raise ValueError('Active suite component hash mismatch')
        batch = load_cases(manifest, mailex_root) if component['benchmark'] == 'frozen' else load_challenge(manifest, mailex_root, benchmark=component['benchmark'])
        if len(batch) != component['cases']:
            raise ValueError('Suite component count mismatch')
        cases.extend(batch)
    if len(cases) != suite['total_cases'] or len({c.case_id for c in cases}) != len(cases):
        raise ValueError('Suite count or IDs mismatch')
    if suite.get('reference_overrides'):
        ref = suite['reference_overrides']
        path = (registry.parent / ref['file']).resolve()
        if not path.is_relative_to(registry.parent.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != ref['sha256']:
            raise ValueError('V2 reference override hash or path mismatch')
        from actionmail.reasoning.multi_response import parse_multi_response
        overrides = json.loads(path.read_text(encoding='utf-8'))['cases']
        if set(overrides) - {c.case_id for c in cases}:
            raise ValueError('Unknown v2 reference override case')
        updated = []
        for case in cases:
            rule = overrides.get(case.case_id)
            if not rule:
                updated.append(case)
                continue
            if 'gold' in rule:
                decision = parse_multi_response(json.dumps(rule['gold']), require_explanation=True)
                quotes = [*decision.evidence, *(e for a in decision.actions for e in a.evidence)]
                if any(e.quote not in case.email.sources().get(e.source_id, '') for e in quotes):
                    raise ValueError('V2 reference evidence is absent from original source')
            outcomes = rule.get('accepted_outcomes', [])
            if any(o['status'] not in {'action', 'no_action', 'needs_review'} or not 0 <= o['action_count'] <= 3 or (o['status'] == 'action') != (o['action_count'] > 0) for o in outcomes):
                raise ValueError('Invalid accepted v2 reference outcome')
            record = {**case.record, 'gold': rule.get('gold', case.gold), 'reference_adjudication': rule,
                      'annotation_note': rule['note'], 'accepted_outcomes': outcomes}
            updated.append(replace(case, record=record))
        cases = updated
    return cases
