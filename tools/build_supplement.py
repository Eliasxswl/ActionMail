"""Build exactly ten pending references; original data is never rewritten."""
import hashlib
import json
from email import policy
from email.parser import BytesParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / 'data'
DEST = ROOT / 'evaluation/supplement_v2.jsonl'


def main():
    if DEST.exists():
        raise SystemExit('Supplement already exists; preserve review-bound references.')
    legacy = {r['case_id']: r for line in (ROOT / 'evaluation/archive/challenge_v2_1_revision2.jsonl').read_text(encoding='utf-8').splitlines()
              if (r := json.loads(line))}
    rows = []
    def original(filename, target, gold, tags, note):
        path = DATA / 'raw_threads' / filename
        rows.append({'category': 'long_content', 'source': {'kind': 'mailex_raw', 'file': filename,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'target_recipient': target, 'include_thread': True},
            'gold': gold, 'feature_tags': tags, 'source_expectations': {}, 'annotation_note': note})
    original('mccarty-d_inbox_alaska_gas_13', 'dennis_mcconaghy@transcanada.com',
        {'status': 'action', 'actions': [{'kind': 'perform_task', 'text': 'Revise the SENR committee letter: replace "substantial progress" with "continued progress", replace "this significant development" with "these developments", and end the letter after the second paragraph.',
         'deadline': None, 'evidence': []}], 'review_reason': None},
        ['original_mailex', 'long_thread', 'multiple_requested_edits', 'recipient_ownership', 'missing_date'],
        'Original source; all edits concern one letter. Candidate grouping as one task requires owner review. No received date is supplied.')
    # Evidence is copied directly from parsed original text, preserving dataset line breaks.
    from actionmail.evaluation.cases import _load_mailex
    rows[0]['case_id'] = 'S01'
    email, _ = _load_mailex(rows[0], DATA)
    rows[0]['gold']['actions'][0]['evidence'] = [{'source_id': 'body', 'quote': line}
        for line in email.body.splitlines() if line.startswith('- In') or line.startswith('We believe the letter')]
    original('lay-k_inbox_40', 'kenneth.lay@enron.com',
        {'status': 'no_action', 'actions': [], 'review_reason': None},
        ['original_mailex', 'long_thread', 'informational_update', 'older_context', 'missing_date'],
        'Original financial update; distinguish the current informative reply from old requests. Candidate no-action label pending owner.')
    provenance = json.loads((ROOT / 'evaluation/real_data_candidates/external_samples.json').read_text(encoding='utf-8'))
    sample = provenance['samples'][0]
    rows.append({'category': 'real_attachments', 'source': {'kind': 'enron_export',
        'file': sample['parent_file'], 'sha256': sample['parent_file_sha256'], 'target_recipient': 'Lynn.Blair@ENRON.com',
        'attachments': [{'name': sample['original_filename'], 'file': sample['local_file'], 'sha256': sample['sha256']}]},
        'gold': {'status': 'no_action', 'actions': [], 'review_reason': None},
        'feature_tags': ['original_enron_export', 'real_pdf', '3000_character_document', 'page_provenance', 'informational_attachment'],
        'source_expectations': {'attachment:1': {'relevance': 'supporting', 'read': 'success'}},
        'annotation_note': 'Actual parent-matched PDF. Body is HTML-to-text rendering of a preserved dataset export. Export date is not a verified received time; leave received_at null. Reference pending owner.'})
    for old_id in ['A04', 'A05', 'P05', 'P02', 'A08', 'H01', 'H04']:
        row = json.loads(json.dumps(legacy[old_id]))
        row['source']['file'] = 'archive/' + row['source']['file']
        row['legacy_fixture_id'] = old_id
        row['annotation_note'] = 'Synthetic gap-coverage fixture; not original dataset mail. ' + row['annotation_note']
        rows.append(row)
    # Keep the synthetic limit example around the owner's requested scale.
    limit_row = rows[-1]
    message = BytesParser(policy=policy.default).parsebytes((ROOT / 'evaluation' / limit_row['source']['file']).read_bytes())
    body = message.get_content()
    message.set_content(body[:2000] + '\n\n' + body[-500:])
    fixture = ROOT / 'evaluation/fixtures_supplement/S10.eml'
    fixture.parent.mkdir(exist_ok=True)
    fixture.write_bytes(message.as_bytes(policy=policy.SMTP))
    limit_row['source'].update(file='fixtures_supplement/S10.eml', sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    limit_row['workflow_limits'] = {'max_total_chars': 2000}
    for index, row in enumerate(rows, 1):
        row.update(case_id=f'S{index:02d}', challenge_version='2.2', review_state='pending_owner', coverage_expectation='complete')
        row.setdefault('evidence_locations', [])
    DEST.write_bytes((''.join(json.dumps(row) + '\n' for row in rows)).encode('utf-8'))
    from actionmail.evaluation.challenge import load_challenge
    cases = load_challenge(DEST, DATA, benchmark='supplement-v2')
    if len(cases) != 10:
        raise ValueError('Expected ten supplementary cases')
    from actionmail.evaluation.cases import load_cases
    base_path = ROOT / 'evaluation/cases.jsonl'
    base = load_cases(base_path, DATA)
    if len({c.case_id for c in [*base, *cases]}) != 60:
        raise ValueError('Active suite must contain sixty distinct cases')
    suite = {'suite': 'v2-60', 'total_cases': 60, 'components': [
        {'benchmark': 'frozen', 'manifest': 'cases.jsonl', 'cases': 50, 'sha256': hashlib.sha256(base_path.read_bytes()).hexdigest()},
        {'benchmark': 'supplement-v2', 'manifest': DEST.name, 'cases': 10, 'sha256': hashlib.sha256(DEST.read_bytes()).hexdigest()}],
        'excluded': ['archive/', 'historical results', 'provenance-only downloads'],
        'supplement_review_state': 'pending_owner'}
    (ROOT / 'evaluation/active_suite.json').write_text(json.dumps(suite, indent=2) + '\n', encoding='utf-8')
    print('Created ten pending supplementary references; no model call.')


if __name__ == '__main__':
    main()
