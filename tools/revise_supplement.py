"""Create a new ten-case reference revision from owner feedback; preserve prior review."""
import hashlib
import json
from email.message import EmailMessage
from email import policy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'evaluation/supplement_v2.jsonl'
NEW = ROOT / 'evaluation/supplement_v2_revision2.jsonl'


def main():
    if NEW.exists():
        raise SystemExit('Revision exists; do not overwrite reviewed references.')
    rows = [json.loads(line) for line in OLD.read_text(encoding='utf-8').splitlines()]
    review = ROOT / 'results/evaluation/supplement-v2-gold-preview/adjudication.json'
    prior = json.loads(review.read_text(encoding='utf-8'))
    if prior['manifest_sha256'] != hashlib.sha256(OLD.read_bytes()).hexdigest():
        raise ValueError('Owner review does not match previous manifest')
    rows[0]['gold'] = {'status': 'no_action', 'actions': [], 'review_reason': None}
    rows[0]['annotation_note'] = 'Owner explicitly corrected the choice: optional comments for consideration do not create an obligation to revise, evaluate or respond. No action for Dennis. Preserve the original email.'
    rows[1]['annotation_note'] = 'Serving kenneth.lay@enron.com. Newest body reports a financial figure; older investment questions are not renewed. No-action proposal remains pending because the owner marked the earlier reference uncertain. This does not assert that the older task was completed.'
    rows[2]['source_expectations']['attachment:1'] = {'relevance': 'irrelevant', 'read': 'skip'}
    rows[2]['annotation_note'] = 'Serving Lynn.Blair@ENRON.com. The newest body is an informative balance report with no requested current task or action dependency. Skip PDF for extraction; original PDF and reference-only extraction remain available for human inspection. New source expectation requires review.'
    rows[4]['source_expectations']['attachment:3'] = {'relevance': 'irrelevant', 'read': 'skip'}
    rows[4]['annotation_note'] = 'Two independently assigned tasks in estimate.txt and design.docx. Historical reference.csv does not help determine either action and is skipped under the revised action-focused reading policy.'
    body = 'Alex, please approve invoice INV-104. Separately, update the public website contact page. Also book the laboratory review room. Finally, send the weekly staffing report.'
    message = EmailMessage()
    message['From'] = 'maya@example.com'
    message['To'] = 'alex@example.com'
    message['Subject'] = 'Four independent requests'
    message['Date'] = 'Wed, 30 Sep 2026 09:00:00 +0800'
    message.set_content(body)
    fixture = ROOT / 'evaluation/fixtures_supplement/S10_revision2.eml'
    fixture.write_bytes(message.as_bytes(policy=policy.SMTP))
    rows[9]['source'] = {'kind': 'authored_eml', 'file': 'fixtures_supplement/S10_revision2.eml',
        'sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(), 'target_recipient': 'alex@example.com', 'snapshots': {}}
    rows[9].pop('workflow_limits', None)
    rows[9]['feature_tags'] = ['four_independent_tasks', 'over_three_actions', 'clear_failure_case']
    rows[9]['gold'] = {'status': 'needs_review', 'actions': [], 'review_reason': 'Four independently completable tasks exceed the three-action limit; no task may be silently dropped.'}
    rows[9]['annotation_note'] = 'Replacement for owner-rejected confusing fixture. Short synthetic email isolates the action limit; no artificial coverage-budget failure or filler.'
    for row in rows:
        row['reference_revision'] = 2
        row['review_state'] = 'pending_owner'
        row['prior_review'] = prior['reviews'].get(row['case_id'])
        row['prior_review_manifest_sha256'] = prior['manifest_sha256']
    NEW.write_bytes(''.join(json.dumps(row) + '\n' for row in rows).encode('utf-8'))
    from actionmail.evaluation.challenge import load_challenge, prepare_challenge
    cases = load_challenge(NEW, ROOT.parent / 'data', benchmark='supplement-v2')
    prepare_challenge(cases, NEW, ROOT / 'results/evaluation/supplement-v2-gold-preview-r2', benchmark='supplement-v2')
    suite_path = ROOT / 'evaluation/active_suite.json'
    suite = json.loads(suite_path.read_text(encoding='utf-8'))
    suite['components'][1].update(manifest=NEW.name, sha256=hashlib.sha256(NEW.read_bytes()).hexdigest())
    suite_path.write_text(json.dumps(suite, indent=2) + '\n', encoding='utf-8')
    print('Created revision 2 with ten pending references. Previous owner review preserved; no model call.')


if __name__ == '__main__':
    main()
