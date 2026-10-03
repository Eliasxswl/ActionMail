"""Common classification scoring; semantic judgments remain separate and blank."""
from collections import defaultdict
import csv
import json
from pathlib import Path
import statistics


def ratio(a, b):
    return a / b if b else None


def report_arm_label(arm, arm_map, config):
    definition = arm_map[arm]
    model = config.get('models', {}).get(definition.get('model'), {})
    api_id = model.get('id')
    names = {
        'openai/gpt-6-luna': 'GPT-6 Luna',
        'z-ai/glm-5.3-flash': 'GLM-5.3 Flash',
        'google/gemini-3.5-flash-lite': 'Gemini 3.5 Flash Lite',
        'google/gemini-3.8-flash': 'Gemini 3.8 Flash',
        'openai/gpt-6.1-sol': 'GPT-6.1 Sol',
        'anthropic/claude-sonnet-5.5': 'Claude Sonnet 5.5',
    }
    name = model.get('display_name') or names.get(api_id, api_id or definition.get('mode', arm))
    mode = definition.get('mode', 'full')
    return name if mode == 'full' else f'{name} ({mode})'


def metrics(rows):
    matrix = {g: {p: 0 for p in ['action', 'no_action', 'needs_review', 'error']}
              for g in ['action', 'no_action', 'needs_review']}
    correct = accepted = counts = quoted = quote_ok = 0
    deadlines = {'non_null_checked': 0, 'non_null_match': 0, 'null_checked': 0, 'null_match': 0}
    for row in rows:
        gold = row['gold']; pred = row['result']['prediction']; status = pred['status'] if pred else 'error'
        matrix[gold['status']][status] += 1
        correct += status == gold['status']
        expected_count = len(gold['actions']) if 'actions' in gold else int(gold['status'] == 'action')
        count = len(pred['actions']) if pred else 0
        alternatives = row['accepted_outcomes']
        if alternatives:
            accepted += any(a['status'] == status and a['action_count'] == count for a in alternatives)
            counts += any(a['status'] == status and a['action_count'] == count for a in alternatives)
        else:
            accepted += status == gold['status']; counts += count == expected_count
        quoted += row['result'].get('quote_count', 0)
        if row['result'].get('quotes_exact'):
            quote_ok += 1
        if gold['status'] == 'action' and pred and status == 'action' and count == 1 and 'deadline' in gold:
            key = 'null' if gold['deadline'] is None else 'non_null'
            deadlines[key + '_checked'] += 1
            deadlines[key + '_match'] += gold['deadline'] == pred['actions'][0]['deadline']
    tp = matrix['action']['action']; fp = matrix['no_action']['action'] + matrix['needs_review']['action']
    fn = sum(matrix['action'].values()) - tp
    reviews = sum(m['needs_review'] for m in matrix.values())
    return {'analyses': len(rows), 'strict_status_match': correct, 'strict_status_rate': ratio(correct, len(rows)),
            'accepted_joint_status_count_match': accepted, 'action_count_match': counts, 'matrix': matrix,
            'action_tp': tp, 'action_fp': fp, 'action_fn': fn,
            'action_precision': ratio(tp, tp + fp), 'action_recall': ratio(tp, tp + fn),
            'action_f1': ratio(2 * tp, 2 * tp + fp + fn), 'review_count': reviews,
            'review_rate': ratio(reviews, len(rows)), 'review_precision': ratio(matrix['needs_review']['needs_review'], reviews),
            'review_recall': ratio(matrix['needs_review']['needs_review'], sum(matrix['needs_review'].values())),
            'unnecessary_reviews': reviews - matrix['needs_review']['needs_review'],
            'quote_count': quoted, 'quote_exact_cases': quote_ok, 'deadlines': deadlines,
            'wall_ms_median': statistics.median(r['wall_ms'] for r in rows) if rows else None,
            'model_errors': sum(bool(r['result'].get('model_error')) for r in rows),
            'semantic_review_complete': False}


def score_run(folder, *, write_report=False):
    folder = Path(folder)
    meta = json.loads((folder / 'run.json').read_text(encoding='utf-8'))
    rows = [json.loads(s) for s in (folder / 'rows.jsonl').read_text(encoding='utf-8').splitlines() if s]
    config = json.loads((folder / 'config.json').read_text(encoding='utf-8'))
    by_arm = defaultdict(list)
    for row in rows:
        by_arm[row['arm']].append(row)
    arm_map = {a['id']: a for a in config['arms']}
    paired = {}
    for arm, batch in by_arm.items():
        comparator = arm_map[arm].get('comparator')
        if not comparator:
            continue
        current = {(r['case_id'], r['trial']): r for r in batch}
        reference = {(r['case_id'], r['trial']): r for r in by_arm.get(comparator, [])}
        shared = sorted(current.keys() & reference.keys())
        paired[arm] = {'comparator': comparator, 'paired_analyses': len(shared),
                      'case_ids': sorted({cid for cid, _ in shared}),
                      'arm': metrics([current[k] for k in shared]),
                      'comparator_metrics': metrics([reference[k] for k in shared]),
                      'missing_comparator_analyses': len(current) - len(shared)}
    groups = defaultdict(list)
    for r in rows:
        groups[(r['arm'], r['case_id'])].append(r)
    stability = []
    for (arm, cid), batch in groups.items():
        if arm_map[arm]['trials'] < 2:
            continue
        signatures = {(r['result']['prediction']['status'], len(r['result']['prediction']['actions'])) for r in batch}
        complete = len(batch) == arm_map[arm]['trials'] and len({r['trial'] for r in batch}) == len(batch)
        stability.append({'arm': arm, 'case_id': cid, 'trials': len(batch), 'complete': complete,
                          'stable_status_count': complete and len(signatures) == 1,
                          'note': 'Agreement alone is not correctness or semantic equivalence.'})
    slices = {}
    for arm, batch in by_arm.items():
        slices[arm] = {}
        for field in ['category', 'origin']:
            values = defaultdict(list)
            for r in batch:
                values[r[field]].append(r)
            slices[arm][field] = {k: metrics(v) for k, v in values.items()}
    calls_path = folder / 'calls.jsonl'
    calls = [json.loads(s) for s in calls_path.read_text(encoding='utf-8').splitlines() if s] if calls_path.exists() else []
    from operations import derive
    operational = derive(folder, rows, calls, config, meta)
    result = {'scope': meta['mode'], 'run_complete': meta['complete'], 'planned_analyses': meta['planned_analyses'],
              'completed_analyses': len(rows), 'classification_policy': 'Strict scalar gold; FN includes review/error on action gold. Approved alternatives reported as joint status/count matches, not substituted into precision/recall.',
              'arms': {k: metrics(v) for k, v in by_arm.items()}, 'paired_comparisons': paired,
              'slices': slices, 'repeatability': stability, 'semantic_review_complete': False,
              'paid_calls': meta['paid_calls'], 'cost': {'reported_usage_estimate_usd': meta['measured_usd'],
              'unknown_usage_calls': sum(c.get('cost_usd') is None for c in calls), 'reservation_usd': meta['reserved_usd']},
              'cost_by_arm': {k: {'reported_usage_estimate_usd': sum(c.get('cost_usd') or 0 for c in calls if c['arm'] == k),
                                     'known_billed_cost_usd': operational['by_arm'][k]['known_billed_cost_usd'],
                                     'unknown_billed_cost_calls': operational['by_arm'][k]['unknown_billed_cost_calls'],
                                     'billed_cost_complete': operational['by_arm'][k]['billed_cost_complete'],
                                     'run_counter_reconciled': bool(operational['actual_consumption_reconciliation'] and operational['actual_consumption_reconciliation']['reconciled']),
                                     'calls': sum(c['arm'] == k for c in calls)} for k in by_arm}}
    (folder / 'summary.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    review_path = folder / 'semantic_review.csv'
    # Never overwrite a worksheet that a human may already have edited.
    if not review_path.exists():
        with review_path.open('x', encoding='utf-8-sig', newline='') as f:
            fields = ['arm', 'trial', 'case_id', 'prediction', 'gold', 'ownership_currentness', 'commitment_faithful',
                      'expected_task_units', 'proposed_task_units', 'matched_task_units', 'deadline_correct',
                      'evidence_supports_meaning', 'review_appropriate', 'reviewer', 'note']
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
            for r in rows:
                w.writerow({'arm': r['arm'], 'trial': r['trial'], 'case_id': r['case_id'],
                            'prediction': json.dumps(r['result']['prediction'], ensure_ascii=False),
                            'gold': json.dumps(r['gold'], ensure_ascii=False)})
    # REPORT.md is the sole maintained human report. Normal scoring updates data
    # and the review worksheet without creating another abbreviated report.
    if not write_report:
        return
    lines = ['# Experiment results', '', f'Mode: {meta["mode"]}. Complete: {meta["complete"]}.', '',
             '| Model / workflow | Analyses | Strict status match | Action precision | Action recall | Review rate |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    def percent(v): return 'N/A' if v is None else f'{100*v:.1f}%'
    for arm, m in result['arms'].items():
        lines.append(f'| {report_arm_label(arm, arm_map, config)} | {m["analyses"]} | {m["strict_status_match"]}/{m["analyses"]} | {percent(m["action_precision"])} | {percent(m["action_recall"])} | {percent(m["review_rate"])} |')
    lines += ['', '## Speed and cost', '',
              '| Model / workflow | Case P50 / P95 ms | Calls | Known billed USD | Missing bill calls | Billed complete |',
              '| --- | ---: | ---: | ---: | ---: | --- |']
    def number(v): return 'N/A' if v is None else f'{v:.2f}'
    for arm, op in operational['by_arm'].items():
        latency = op['case_wall_ms']
        lines.append(f'| {report_arm_label(arm, arm_map, config)} | {number(latency["p50"])} / {number(latency["p95"])} | {op["calls"]} | {op["known_billed_cost_usd"]:.6f} | {op["unknown_billed_cost_calls"]} | {op["billed_cost_complete"]} |')
    audit = operational['actual_consumption_reconciliation']
    lines += ['', 'Actual consumption is measured by before/after usage counters and reconciled against per-generation billed costs. Token-rate estimates remain budget forecasts only.']
    if audit:
        lines += [f'API-key usage delta USD: {audit["key_usage_delta_usd"]}. Account usage delta USD: {audit["account_usage_delta_usd"]}. Balance decrease USD: {audit["account_balance_decrease_usd"]}.',
                  f'Generation bills reconciled: {audit["reconciled"]}. Gap USD: {audit["key_delta_minus_generation_sum_usd"]}.', audit['attribution']]
    else:
        lines += ['Actual-consumption accounting unavailable for this historical/offline/scripted run; do not replace it with an estimated actual cost.']
    lines += ['', 'Per-case and per-call details: case_metrics.csv, turn_metrics.csv, operations.json; original logs: rows.jsonl, calls.jsonl, events.jsonl.',
              'TTFT is unavailable with non-streaming requests. Speed includes transport/queueing; token/s is end-to-end, not decode throughput.',
              'See operations.json for denominators, token totals, repair incidence, incomplete-case calls, provider-reported costs and cross-model case agreement.']
    lines += ['', 'Semantic judgment fields are blank. Scripted smoke scores are engineering checks, never model accuracy.',
              'Read paired comparisons on shared case IDs, not whole-arm aggregates with different denominators.',
              'Null deadlines and supported non-null dates are scored separately; task count is not task completeness.',
              'Unknown-usage or failed calls may still be billed; recorded cost is incomplete when those exist.']
    (folder / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def score_review(folder):
    """Validate human matches without interpreting natural-language task meaning in code."""
    folder = Path(folder)
    rows = [json.loads(s) for s in (folder / 'rows.jsonl').read_text(encoding='utf-8').splitlines() if s]
    originals = {(r['arm'], str(r['trial']), r['case_id']): r for r in rows}
    with (folder / 'semantic_review.csv').open(encoding='utf-8-sig', newline='') as f:
        reviews = list(csv.DictReader(f))
    seen = set(); accepted = defaultdict(list); pending = 0
    checks = ['ownership_currentness', 'commitment_faithful', 'deadline_correct',
              'evidence_supports_meaning', 'review_appropriate']
    for r in reviews:
        key = (r['arm'], r['trial'], r['case_id'])
        if key in seen or key not in originals:
            raise ValueError('Duplicate/unknown semantic review row')
        seen.add(key)
        original = originals[key]
        if json.loads(r['prediction']) != original['result']['prediction'] or json.loads(r['gold']) != original['gold']:
            raise ValueError('Review worksheet changed frozen gold or prediction; adjudicate separately')
        if not r['reviewer'].strip() or any(not r[k].strip() for k in checks + ['expected_task_units', 'proposed_task_units', 'matched_task_units']):
            pending += 1
            continue
        if any(r[k].lower() not in ['yes', 'no', 'na'] for k in checks):
            raise ValueError('Semantic criteria must be yes/no/na')
        expected, proposed, matched = (int(r[k]) for k in ['expected_task_units', 'proposed_task_units', 'matched_task_units'])
        actual_proposed = len(original['result']['prediction']['actions'])
        if min(expected, proposed, matched) < 0 or matched > min(expected, proposed) or proposed != actual_proposed:
            raise ValueError('Invalid task matching counts')
        gold = original['gold']
        reference_count = len(gold['actions']) if 'actions' in gold else int(gold['status'] == 'action')
        allowed_counts = {reference_count, *(a['action_count'] for a in original['accepted_outcomes'])}
        if expected not in allowed_counts:
            raise ValueError('Expected task count changes frozen references; adjudicate separately')
        accepted[r['arm']].append({'expected': expected, 'proposed': proposed, 'matched': matched,
                                  'criteria': {k: r[k].lower() for k in checks}, 'reviewer': r['reviewer']})
    if seen != set(originals):
        raise ValueError('Missing semantic review rows')
    result = {'scope': 'Explicitly attributed reviewer judgments; identity/independence not automatically verified',
              'reviewed_analyses': sum(len(v) for v in accepted.values()), 'pending_analyses': pending,
              'complete': pending == 0 and len(reviews) == len(rows), 'arms': {}}
    for arm, batch in accepted.items():
        expected = sum(r['expected'] for r in batch); proposed = sum(r['proposed'] for r in batch); matched = sum(r['matched'] for r in batch)
        result['arms'][arm] = {'reviewed_analyses': len(batch), 'expected_tasks': expected, 'proposed_tasks': proposed,
                              'matched_tasks': matched, 'semantic_precision': ratio(matched, proposed),
                              'semantic_recall': ratio(matched, expected), 'omissions': expected - matched,
                              'false_additions': proposed - matched,
                              'reviewers': sorted({r['reviewer'] for r in batch}),
                              'criteria': {k: {answer: sum(r['criteria'][k] == answer for r in batch)
                                                for answer in ['yes', 'no', 'na']} for k in checks}}
    (folder / 'semantic_summary.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'Semantic review: {result["reviewed_analyses"]} completed, {pending} pending')
