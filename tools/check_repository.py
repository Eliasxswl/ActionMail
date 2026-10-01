"""Check active inputs, archive relocation and current Markdown links without API calls."""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from actionmail.evaluation.suite import load_suite


def main():
    cases = load_suite(ROOT / 'evaluation/active_suite.json', ROOT.parent / 'data')
    assert len(cases) == 60
    checked, local_missing = 0, 0
    for move in json.loads((ROOT / 'backup/migration.json').read_text(encoding='utf-8-sig')):
        target = ROOT / move['destination']
        for item in move['files']:
            path = target if item['file'] == '.' else target / item['file'].replace('\\', '/')
            if not path.exists() and ('/data/' in move['destination'] or '/code/generated/' in move['destination'] or move['destination'].endswith('.zip')):
                local_missing += 1
                continue
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], str(path)
            checked += 1
    docs = [ROOT / 'README.md', ROOT / 'backup/README.md', *ROOT.glob('docs/*.md'), ROOT / 'docs/course/README.md']
    for document in docs:
        for link in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
            if '://' not in link and not link.startswith('#'):
                assert (document.parent / link.split('#')[0]).exists(), f'{document}: {link}'
    rows = [json.loads(line) for line in (ROOT / 'results/evaluation/v2-regression-repair-20261001/cases.jsonl').read_text(encoding='utf-8').splitlines()]
    assert {r['case_id'] for r in rows} == {c.case_id for c in cases}
    print(f'Validated 60 active cases, {checked} archived file hashes and current document links; {local_missing} local-only archive files absent.')


if __name__ == '__main__':
    main()
