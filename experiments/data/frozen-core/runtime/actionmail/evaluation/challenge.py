"""Load a separately versioned development challenge; pending gold is never scored."""
import hashlib
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
from actionmail.evaluation.cases import EvaluationCase, _load_mailex
from actionmail.ingestion.eml import load_eml
from actionmail.content.reader import read_external_sources
from actionmail.reasoning.multi_response import parse_multi_response
from actionmail.domain.email import SourceText
from actionmail.domain.email import ExternalSource, EmailPackage
from actionmail.content.reader import _text_from_bytes

GROUP_COUNTS = {'long_content': 6, 'real_attachments': 8, 'links_mixed': 6, 'limits_hostile': 4}

def load_challenge(manifest, mailex_root, *, benchmark='challenge-v2.1'):
    records = [json.loads(line) for line in manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
    expected = GROUP_COUNTS if benchmark == 'challenge-v2.1' else {'long_content': 2, 'real_attachments': 4, 'links_mixed': 2, 'limits_hostile': 2}
    version = '2.1' if benchmark == 'challenge-v2.1' else '2.2'
    if benchmark not in {'challenge-v2.1', 'supplement-v2'} or Counter(r['category'] for r in records) != expected:
        raise ValueError(f'{benchmark} requires category counts {expected}')
    if len({r['case_id'] for r in records}) != len(records):
        raise ValueError('Duplicate challenge case ID')
    cases = []
    for r in records:
        if r.get('challenge_version') != version or r.get('review_state') not in {'pending_owner', 'approved'} or not r.get('feature_tags'):
            raise ValueError('Challenge version, review state and feature tags are required')
        source = r['source']
        if source['kind'] == 'mailex_raw':
            email, digest = _load_mailex(r, mailex_root)
        elif source['kind'] == 'authored_eml':
            path = (manifest.parent / source['file']).resolve()
            if not path.is_relative_to(manifest.parent.resolve()):
                raise ValueError('Challenge fixture path escapes manifest directory')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if source['sha256'] != digest:
                raise ValueError('Challenge fixture hash mismatch')
            email = replace(load_eml(path, source['target_recipient']), case_id=r['case_id'])
            snapshots = source.get('snapshots', {})
            if set(snapshots) - {s.source_id for s in email.external_sources if s.kind == 'link'}:
                raise ValueError('Snapshot ID not present in link inventory')
            email = replace(email, external_sources=tuple(replace(s, snapshot_text=snapshots.get(s.source_id)) for s in email.external_sources))
            email = replace(email, thread=tuple(SourceText(**s) for s in source.get('thread', [])))
        elif source['kind'] == 'enron_export':
            def verified(relative, expected_hash):
                path = (mailex_root / relative).resolve()
                if not path.is_relative_to(mailex_root.resolve()):
                    raise ValueError('Export source escapes data directory')
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != expected_hash:
                    raise ValueError('Export source hash mismatch')
                return raw
            raw = verified(source['file'], source['sha256'])
            parent = json.loads(raw)
            target = source['target_recipient']
            to = tuple(x['email'] for x in parent['to'])
            cc = tuple(x['email'] for x in parent['cc'])
            if target.lower() not in {x.lower() for x in (*to, *cc)}:
                raise ValueError('Target absent from original export recipients')
            attachments = []
            for index, item in enumerate(source['attachments'], 1):
                matches = [a for a in parent['attachments'] if a['filename'] == item['name']]
                content = verified(item['file'], item['sha256'])
                if len(matches) != 1 or matches[0]['size'] != len(content):
                    raise ValueError('Attachment is not uniquely bound to exported parent')
                attachments.append(ExternalSource(f'attachment:{index}', 'attachment', item['name'], content=content))
            if len(attachments) != len(parent['attachments']):
                raise ValueError('Export attachment inventory is incomplete')
            body = _text_from_bytes(ExternalSource('body', 'attachment', 'body.html', content=parent['body'].encode('utf-8'), media_type='text/html', charset='utf-8'))
            email = EmailPackage(r['case_id'], target, None, parent['from']['email'], tuple(dict.fromkeys((*to, *cc))),
                                 parent['subject'], body, to_recipients=to, cc_recipients=cc, external_sources=tuple(attachments))
            digest = source['sha256']
        else:
            raise ValueError('Unknown challenge authorship')
        ids = {s.source_id for s in email.external_sources}
        expectations = r['source_expectations']
        if set(expectations) != ids:
            raise ValueError('Source expectations must cover complete inventory')
        if any(e.get('relevance') not in {'decisive', 'supporting', 'irrelevant', 'unresolved'} or e.get('read') not in {'success', 'failure', 'skip'} for e in expectations.values()):
            raise ValueError('Invalid source expectation')
        gold = parse_multi_response(json.dumps(r['gold']))
        if gold.action_count > 3:
            raise ValueError('Challenge gold exceeds product action limit')
        read = read_external_sources(email)
        texts = read.email.sources()
        for a in gold.actions:
            for e in a.evidence:
                if not e.quote.strip() or e.quote not in texts.get(e.source_id, ''):
                    raise ValueError(f'Challenge evidence absent: {r["case_id"]} {e.source_id}')
        for expected in r.get('evidence_locations', []):
            record = next((x for x in read.records if x.source_id == expected['source_id']), None)
            if record is None or not any(loc.label == expected['location'] and expected['quote'] in record.extracted_text[loc.start:loc.end] for loc in record.locations):
                raise ValueError('Expected evidence location absent')
        cases.append(EvaluationCase(r, email, digest))
    return cases


def prepare_challenge(cases, manifest, output, *, benchmark='challenge-v2.1'):
    """Make a reviewable reference-only run with no model calls or scoring."""
    from datetime import datetime, timezone
    from dataclasses import asdict
    output.mkdir(parents=True, exist_ok=False)
    now = datetime.now(timezone.utc).isoformat()
    run = {'run_id': output.name, 'engine': 'reference-preview', 'schema': 'v2', 'benchmark': benchmark,
           'model': 'no model call', 'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
           'started_at_utc': now, 'case_ids': [c.case_id for c in cases]}
    (output / 'run.json').write_text(json.dumps(run, indent=2) + '\n', encoding='utf-8')
    rows = []
    for c in cases:
        outcome = read_external_sources(c.email)
        rows.append({'case_id': c.case_id, 'category': c.record['category'], 'gold': c.gold, 'prediction': None,
                     'status_correct': None, 'action_count_match': None, 'reference_review_state': c.record.get('review_state', 'approved'),
                     'read_sources': [asdict(r) for r in outcome.records], 'reference_extraction_only': True,
                     'read_failures': list(outcome.failures), 'feature_tags': c.record.get('feature_tags', []),
                     'raw_model_response': None, 'validation_errors': [], 'error': None, 'model_calls': 0})
    (output / 'cases.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    return output


def approve_challenge_gold(manifest, review_dir, destination):
    """Create a new manifest only after all reference judgments are explicitly correct."""
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    run = json.loads((review_dir / 'run.json').read_text(encoding='utf-8'))
    review_path = review_dir / 'adjudication.json'
    judgments = json.loads(review_path.read_text(encoding='utf-8'))
    if run.get('engine') != 'reference-preview' or run.get('manifest_sha256') != digest or judgments.get('manifest_sha256') != digest or judgments.get('run_id') != run.get('run_id'):
        raise ValueError('Gold approval requires the matching reference-preview adjudication')
    records = [json.loads(line) for line in manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
    if any(judgments.get('reviews', {}).get(r['case_id'], {}).get('gold_label') != 'correct' for r in records):
        raise ValueError('Every challenge reference must be explicitly reviewed correct before approval')
    if destination.exists() or destination.resolve() == manifest.resolve():
        raise ValueError('Approval must write a new manifest; never overwrite existing gold')
    for r in records:
        r['review_state'] = 'approved'
        r['reference_approval'] = {'run_id': run['run_id'], 'adjudication_sha256': hashlib.sha256(review_path.read_bytes()).hexdigest(), 'pending_manifest_sha256': digest}
    destination.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')
    return destination

def challenge_checks(case, run):
    approved = case.record['review_state'] == 'approved'
    expected = case.record['source_expectations']
    plans = {s.source_id: s.relevance for s in run.source_plan}
    reads = {s.source_id for s in run.read_records}
    failures = {f.split(': ', 1)[0] for f in run.read_failures}
    selection = all(plans.get(sid) == item['relevance'] for sid, item in expected.items())
    reading = all((sid in reads if item['read'] == 'success' else sid in failures if item['read'] == 'failure' else sid not in reads) for sid, item in expected.items())
    ranges = {}
    for item in run.coverage:
        ranges.setdefault(item['source_id'], []).append((item['start'], item['end']))
    texts = {**case.email.sources(), **{r.source_id: r.extracted_text for r in run.read_records}}
    full = True
    for sid, text in texts.items():
        if not text:
            continue
        end = 0
        for start, stop in sorted(ranges.get(sid, [])):
            if start > end:
                break
            end = max(end, stop)
        full &= end == len(text)
    return {'reference_review_state': case.record['review_state'],
            'status_correct': run.decision.status == case.gold['status'] if approved else None,
            'action_count_match': run.decision.action_count == len(case.gold['actions']) if approved else None,
            'source_selection_match': selection if approved else None,
            'read_expectation_match': reading if approved else None,
            'content_coverage_complete': full,
            'manual_action_completeness': None, 'manual_deadline_correct': None,
            'feature_tags': case.record['feature_tags']}
