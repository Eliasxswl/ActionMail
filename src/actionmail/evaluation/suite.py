"""Load the hash-bound active suite without changing either historical manifest."""
import hashlib
import json
from pathlib import Path
from actionmail.evaluation.cases import load_cases
from actionmail.evaluation.challenge import load_challenge


def load_suite(registry: Path, mailex_root: Path):
    suite = json.loads(registry.read_text(encoding='utf-8'))
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
    return cases
