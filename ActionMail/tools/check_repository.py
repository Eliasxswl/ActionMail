"""Check submission inputs, sealed experiment hashes and maintained links offline."""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
sys.path.insert(0, str(ROOT / 'src'))
from actionmail.evaluation.suite import load_suite


def main():
    cases = load_suite(ROOT / 'evaluation/active_suite.json', ROOT.parent / 'data')
    assert len(cases) == 60
    experiment = WORKSPACE / 'experiments'
    sealed = json.loads((experiment / 'results/finalization.json').read_text(encoding='utf-8'))
    for item in sealed['files']:
        path = (experiment / item['path']).resolve()
        assert path.is_relative_to(experiment.resolve()), item['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], item['path']
    bundle = experiment / 'data/frozen-core'
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    for relative, digest in manifest['files'].items():
        path = (bundle / relative).resolve()
        assert path.is_relative_to(bundle.resolve()), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, relative
    docs = [WORKSPACE / 'README.md', ROOT / 'README.md', *ROOT.glob('docs/*.md'),
            ROOT / 'evaluation/annotation_policy.md', *experiment.glob('*.md'),
            WORKSPACE / 'data/README.md', WORKSPACE / 'report/README.md']
    for document in docs:
        for link in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
            if '://' not in link and not link.startswith('#'):
                assert (document.parent / link.split('#')[0]).exists(), f'{document}: {link}'
    rows = [json.loads(line) for line in (ROOT / 'results/evaluation/v2-regression-repair-20261001/cases.jsonl').read_text(encoding='utf-8').splitlines()]
    assert {r['case_id'] for r in rows} == {c.case_id for c in cases}
    assert not (ROOT / 'backup').exists(), 'Expanded history belongs in the historical ZIP'
    print(f'Validated 60 active cases, {len(sealed["files"])} sealed experiment files, '
          f'{len(manifest["files"])} runtime bundle files, {len(docs)} maintained documents.')


if __name__ == '__main__':
    main()
