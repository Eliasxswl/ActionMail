"""Verify downloaded public samples offline; does not synthesize mail or call a model."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from actionmail.content.reader import extract
from actionmail.domain.email import ExternalSource

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / 'data'
BASE = 'https://huggingface.co/datasets/enronarchive/mail/resolve/main/mail/blair-l/'


def main():
    index = DATA / 'enron_blair_index.json'
    emails = json.loads(index.read_text(encoding='utf-8'))['emails']
    result = {'mailbox_index_url': BASE + 'index.json',
              'mailbox_index_sha256': hashlib.sha256(index.read_bytes()).hexdigest(),
              'email_count': len(emails),
              'attachment_reference_extensions': dict(Counter(Path(a['filename']).suffix.lower()
                  for e in emails for a in e['attachments'])), 'samples': []}
    specs = [
        ('enron_nov25.pdf', '496fbb1c751d22557bfd74a63732c608', 'nov25.pdf'),
        ('enron_feedback.doc', '00a44f790251c904faa3fa72e25942cf', 'Customer Feedback Action Plan 0901.doc'),
        ('w3c_storage_buckets.pdf', None, 'TPAC_2020_Storage_Buckets_API.pdf'),
    ]
    for local, parent_id, original_name in specs:
        path = DATA / 'external_samples' / local
        raw = path.read_bytes()
        record = {'local_file': 'external_samples/' + local, 'original_filename': original_name,
                  'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                  'signature_hex': raw[:8].hex()}
        if parent_id:
            parent = next(e for e in emails if e['id'] == parent_id)
            attachment = next(a for a in parent['attachments'] if a['filename'] == original_name)
            if attachment['size'] != len(raw):
                raise ValueError('Downloaded attachment size differs from parent index')
            parent_path = path.parent / (parent_id + '.parent.json')
            parent_path.write_text(json.dumps(parent, indent=2) + '\n', encoding='utf-8')
            record.update(parent_id=parent_id, parent_subject=parent['subject'],
                          parent_file=parent_path.relative_to(DATA).as_posix(),
                          parent_file_sha256=hashlib.sha256(parent_path.read_bytes()).hexdigest(),
                          download_url=BASE + attachment['path'].replace(' ', '%20'),
                          date_policy='Mirror date field is preserved in parent JSON, not promoted to verified received_at.')
        else:
            record.update(parent_url='https://lists.w3.org/Archives/Public/www-archive/2020Nov/0000.html',
                parent_file='w3c_storage_parent.html',
                parent_file_sha256=hashlib.sha256((DATA / 'w3c_storage_parent.html').read_bytes()).hexdigest(),
                download_url='https://lists.w3.org/Archives/Public/www-archive/2020Nov/att-0000/' + original_name,
                date_policy='Archive explicitly distinguishes sent time and received time; preserve both.')
        try:
            text, locations = extract(ExternalSource('attachment:1', 'attachment', original_name, content=raw))
            record.update(extraction='success', extracted_chars=len(text), location_count=len(locations))
        except ValueError as exc:
            record.update(extraction='unsupported_or_failed', reason=str(exc))
        result['samples'].append(record)
    destination = ROOT / 'evaluation/real_data_candidates/external_samples.json'
    destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
