"""Inventory unmodified MailEx sources and stage a real-first selection, without gold."""
import hashlib
import json
import re
from pathlib import Path

from actionmail.evaluation.cases import _raw_block

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / 'data'
OUT = ROOT / 'evaluation' / 'real_data_candidates'

# Manual selection is explicit and reproducible; these are not approved reference labels.
SELECTED = {
    'mims-thurston-p_inbox_280': ('l..mims@enron.com', 'Longest raw thread; empty newest body must remain visible.'),
    'mccarty-d_inbox_alaska_gas_110': ('danny.mccarty@enron.com', 'Business proposal thread; original attachment is missing.'),
    'mims-thurston-p_inbox_103': ('patrice.mims@enron.com', 'Long business conversation; empty newest body.'),
    'lay-k_inbox_40': ('kenneth.lay@enron.com', 'Financial update with older context; distinguish information from requests.'),
    'blair-l_inbox_180': ('bradley.holmes@enron.com', 'Operational update; target comes from newest To, not mailbox filename.'),
    'lay-k_inbox_1823': ('kenneth.lay@enron.com', 'Long supportive reply, useful negative candidate.'),
    'blair-l_inbox_279': ('lynn.blair@enron.com', 'Meeting discussion and participation question across recipients.'),
    'mccarty-d_inbox_alaska_gas_13': ('dennis_mcconaghy@transcanada.com', 'Several requested edits to a letter; possible multi-action candidate.'),
    'mccarty-d_inbox_alaska_gas_30': ('eric.gadd@enron.com', 'Written communication request and responsibility in prior context.'),
    'rapp-b_inbox_199': ('bill.rapp@enron.com', 'Two rate questions; original schedule attachment is unavailable.'),
    'lay-k_inbox_171': ('louise.kitchen@enron.com', 'Explicit recipient-specific review request; referenced links are absent.'),
    'derrick-j_inbox_239': ('james.derrick@enron.com', 'Business question and a literal URL; inspect whether link is relevant.'),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frozen = {r['source'].get('file') for line in (ROOT / 'evaluation/cases.jsonl').read_text(encoding='utf-8').splitlines()
              if (r := json.loads(line))['source']['kind'] == 'mailex_raw'}
    rows = []
    for path in sorted((DATA / 'raw_threads').iterdir()):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        text = raw.decode('utf-8', errors='replace')
        blocks = [b.strip() for b in re.split(r'(?m)^-{20,}\s*$', text) if b.strip()]
        parsed = [_raw_block(b) for b in blocks]
        sender, to, cc, subject, body = parsed[0]
        rows.append({'file': path.name, 'sha256': hashlib.sha256(raw).hexdigest(), 'subject': subject,
                     'sender': sender, 'to': to, 'cc': cc, 'received_at': None,
                     'newest_body_chars': len(body), 'body_thread_chars': sum(len(p[4]) for p in parsed),
                     'message_count': len(blocks), 'urls': sorted(set(re.findall(r'https?://[^\s<>\"]+', text))),
                     'attachment_mention': bool(re.search(r'attach', text, re.I)),
                     'in_frozen_manifest': path.name in frozen})
    selected = []
    for row in rows:
        if row['file'] not in SELECTED:
            continue
        target, reason = SELECTED[row['file']]
        actual = {x.strip().lower() for x in (row['to'] + ',' + row['cc']).split(',') if x.strip()}
        if target.lower() not in actual:
            raise ValueError(f'Target absent from actual newest recipients: {row["file"]}')
        if row['in_frozen_manifest']:
            raise ValueError(f'Candidate duplicates frozen case: {row["file"]}')
        selected.append({'candidate_id': f'R{len(selected)+1:02d}', 'origin': 'original_mailex_raw',
                         'review_state': 'unlabelled', 'source': {'kind': 'mailex_raw', 'file': row['file'],
                         'sha256': row['sha256'], 'target_recipient': target, 'include_thread': True},
                         'selection_reason': reason, 'received_at': None,
                         'newest_body_chars': row['newest_body_chars'], 'body_thread_chars': row['body_thread_chars']})
    if len(selected) != len(SELECTED):
        raise ValueError('Some selected raw files are missing')
    summary = {'raw_files': len(rows), 'files_with_literal_http_urls': sum(bool(r['urls']) for r in rows),
               'files_mentioning_attach': sum(r['attachment_mention'] for r in rows),
               'max_body_thread_chars': max(r['body_thread_chars'] for r in rows),
               'max_newest_body_chars': max(r['newest_body_chars'] for r in rows),
               'selected': len(selected), 'notes': ['Character counts are not model tokens.',
               'Attachment mentions do not establish that a binary attachment is available.',
               'Raw MailEx has no newest Date header; received_at is unknown.',
               'Candidates contain no gold labels and must not be scored.']}
    (OUT / 'inventory.json').write_text(json.dumps({'summary': summary, 'files': rows}, indent=2) + '\n', encoding='utf-8')
    (OUT / 'selection.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in selected), encoding='utf-8')
    lines = ['# Original MailEx candidates', '', 'Unlabelled source selection, not an evaluation manifest. '
             'Original files remain untouched. Missing timestamps and attachments are not reconstructed.', '',
             '| ID | Source | Body + thread characters | Target recipient | Selection reason |',
             '| --- | --- | ---: | --- | --- |']
    for r in selected:
        file = r['source']['file']
        lines.append(f'| {r["candidate_id"]} | [{file}](../../../data/raw_threads/{file}) | '
                     f'{r["body_thread_chars"]} | {r["source"]["target_recipient"]} | {r["selection_reason"]} |')
    (OUT / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
