"""Reuse explicit owner judgments only when their reference and reading expectations are unchanged."""
import hashlib
import json
from pathlib import Path

from actionmail.evaluation.cli import PROJECT_ROOT, DEFAULT_MAILEX_ROOT
from actionmail.evaluation.review import ReviewDataset


def main():
    old = PROJECT_ROOT / 'evaluation/supplement_v2.jsonl'
    new = PROJECT_ROOT / 'evaluation/supplement_v2_revision2.jsonl'
    prior_path = PROJECT_ROOT / 'results/evaluation/supplement-v2-gold-preview/adjudication.json'
    prior = json.loads(prior_path.read_text(encoding='utf-8'))
    if prior['manifest_sha256'] != hashlib.sha256(old.read_bytes()).hexdigest():
        raise ValueError('Prior judgment does not match original references')
    dataset = ReviewDataset.open(PROJECT_ROOT / 'results/evaluation/supplement-v2-gold-preview-r2', new, DEFAULT_MAILEX_ROOT)
    previous = {r['case_id']: r for line in old.read_text(encoding='utf-8').splitlines() if (r := json.loads(line))}
    fields = ('source', 'gold', 'source_expectations', 'workflow_limits', 'coverage_expectation', 'evidence_locations')
    carried = []
    for cid, case in dataset.cases.items():
        review = prior['reviews'].get(cid)
        if cid in dataset.reviews() or not review or review['gold_label'] != 'correct':
            continue
        if all(case.record.get(f) == previous[cid].get(f) for f in fields):
            payload = {f: review[f] for f in ('action_meaning', 'evidence_support', 'gold_label', 'note')}
            payload['note'] = f'Owner judgment carried from unchanged reference in {prior["run_id"]}. ' + payload['note']
            dataset.save_review(cid, payload)
            carried.append(cid)
    # The owner explicitly corrected the choice in chat to no_action; this is not inferred from old gold.
    if 'S01' not in dataset.reviews():
        if dataset.cases['S01'].gold['status'] != 'no_action':
            raise ValueError('S01 must match the explicit owner correction')
        dataset.save_review('S01', {'action_meaning': '', 'evidence_support': '', 'gold_label': 'correct',
            'note': 'Owner explicitly corrected the chat choice: comments for consideration alone do not trigger an action. This supersedes the prior reference judgment.'})
    print('Carried unchanged owner judgments:', ', '.join(carried), '; S01 follows explicit chat correction.')


if __name__ == '__main__':
    main()
