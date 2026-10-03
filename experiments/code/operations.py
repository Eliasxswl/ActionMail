"""Derived speed/cost tables with explicit missing-data denominators."""
from collections import defaultdict
import csv
import json
import statistics


def distribution(values):
    values = sorted(v for v in values if isinstance(v, (int, float)))
    def percentile(q):
        if not values:
            return None
        pos = (len(values) - 1) * q
        lo = int(pos); hi = min(lo + 1, len(values) - 1)
        return values[lo] + (values[hi] - values[lo]) * (pos - lo)
    return {'observations': len(values), 'mean': statistics.mean(values) if values else None,
            'p50': percentile(.5), 'p95': percentile(.95), 'max': max(values) if values else None}


def write_csv(path, records):
    # Empty tables still have a readable marker rather than disappearing silently.
    fields = list(dict.fromkeys(k for r in records for k in r)) or ['no_observations']
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fields); writer.writeheader(); writer.writerows(records)


def derive(folder, rows, calls, config, meta):
    def key(r): return r['arm'], r['case_id'], r['trial']
    generation_path = folder / 'generations.jsonl'
    generations = [json.loads(line) for line in generation_path.read_text(encoding='utf-8').splitlines() if line] if generation_path.exists() else []
    generation_index = {(key(g), g['call']): g.get('data', {}) for g in generations}
    billing_path = folder / 'billing.json'
    billing = json.loads(billing_path.read_text(encoding='utf-8')) if billing_path.exists() else None
    grouped = defaultdict(list)
    turns = []
    for c in calls:
        grouped[key(c)].append(c)
        reply = c.get('reply') or {}
        raw = (c.get('transport') or {}).get('response_json') or {}
        raw = raw if isinstance(raw, dict) else {}
        usage = raw.get('usage') or {}
        usage = usage if isinstance(usage, dict) else {}
        choices = raw.get('choices') or []
        choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
        reported_cost = usage.get('cost')
        generation = generation_index.get((key(c), c['call']), {})
        generation_cost = generation.get('total_cost')
        billed = generation_cost if isinstance(generation_cost, (int, float)) else reported_cost
        billed = billed if isinstance(billed, (int, float)) else None
        turns.append({'arm': c['arm'], 'case_id': c['case_id'], 'trial': c['trial'], 'call': c['call'],
                      'turn_id': c.get('turn_id'), 'started_utc': c.get('started_utc'), 'ended_utc': c.get('ended_utc'),
                      'requested_model': c.get('model_requested'), 'resolved_model': reply.get('model') or raw.get('model'),
                      'response_id': raw.get('id'), 'provider': generation.get('provider_name') or raw.get('provider'),
                      'finish_reason': choice.get('finish_reason'), 'error': c.get('error'),
                      'wall_ms': c.get('wall_ms'), 'input_tokens': reply.get('input_tokens', usage.get('prompt_tokens')),
                      'output_tokens': reply.get('output_tokens', usage.get('completion_tokens')),
                      'usage_json': json.dumps(usage, ensure_ascii=False),
                      'estimated_cost_usd': c.get('cost_usd'),
                      'billed_cost_usd': billed,
                      'billed_cost_source': 'generation.total_cost' if isinstance(generation_cost, (int, float)) else 'response.usage.cost' if billed is not None else 'unavailable',
                      'key_usage_delta_usd': (c.get('transport') or {}).get('key_usage_delta_usd'),
                      'openrouter_latency_ms': generation.get('latency'),
                      'openrouter_generation_time_ms': generation.get('generation_time'),
                      'native_tokens_prompt': generation.get('native_tokens_prompt'),
                      'native_tokens_completion': generation.get('native_tokens_completion'),
                      'native_tokens_reasoning': generation.get('native_tokens_reasoning'),
                      'native_tokens_cached': generation.get('native_tokens_cached'),
                      'is_validation_repair': c.get('is_validation_repair', False),
                      'prior_turn_id': c.get('prior_turn_id'),
                      'repair_feedback_json': json.dumps(c.get('repair_feedback'), ensure_ascii=False),
                      'provider_reported_cost_usd': reported_cost if isinstance(reported_cost, (int, float)) else None,
                      'reservation_usd': c.get('reservation_usd'), 'ttft_ms': None,
                      'output_tokens_per_second_end_to_end': (reply['output_tokens'] * 1000 / c['wall_ms'])
                          if isinstance(reply.get('output_tokens'), int) and c.get('wall_ms', 0) > 0 else None,
                      'raw_trace_file': 'calls.jsonl'})
    cases = []
    indexed = {}
    for r in rows:
        batch = grouped[key(r)]; result = r['result']; prediction = result['prediction']
        case_turns = [t for t in turns if key(t) == key(r)]
        reported = [t['provider_reported_cost_usd'] for t in case_turns if t['provider_reported_cost_usd'] is not None]
        billed = [t['billed_cost_usd'] for t in case_turns if t['billed_cost_usd'] is not None]
        repair_turns = [t for t in case_turns if t['is_validation_repair']]
        repair_billed = [t['billed_cost_usd'] for t in repair_turns if t['billed_cost_usd'] is not None]
        known = [c['cost_usd'] for c in batch if c.get('cost_usd') is not None]
        # Calls absent from scripted runs are unmetered fixtures, not zero-cost inference.
        complete_cost = len(known) == len(batch) and meta['mode'] != 'scripted engineering'
        p = {'arm': r['arm'], 'case_id': r['case_id'], 'trial': r['trial'], 'category': r['category'], 'origin': r['origin'],
             'started_utc': r.get('started_utc'), 'ended_utc': r.get('ended_utc'), 'wall_ms': r['wall_ms'],
             'model_call_wall_ms': sum(c.get('wall_ms', 0) for c in batch), 'calls': len(batch),
             'input_tokens_known_sum': sum(t['input_tokens'] or 0 for t in case_turns),
             'output_tokens_known_sum': sum(t['output_tokens'] or 0 for t in case_turns),
             'unknown_input_token_calls': sum(t['input_tokens'] is None for t in case_turns),
             'unknown_output_token_calls': sum(t['output_tokens'] is None for t in case_turns),
             'known_usage_calls': len(known), 'unknown_cost_calls': len(batch) - len(known),
             'known_estimated_cost_usd': sum(known), 'cost_complete': complete_cost,
             'estimated_cost_usd': sum(known) if complete_cost else None,
             'billed_cost_usd': sum(billed) if len(billed) == len(batch) and meta['mode'] != 'scripted engineering' else None,
             'unknown_billed_cost_calls': len(batch) - len(billed),
             'repair_wall_ms': sum(t['wall_ms'] or 0 for t in repair_turns),
             'repair_billed_cost_usd': sum(repair_billed) if len(repair_billed) == len(repair_turns) and meta['mode'] != 'scripted engineering' else None,
             'repair_events_json': json.dumps(result.get('repairs', []), ensure_ascii=False),
             'repair_validated': sum(e.get('outcome') == 'validated' for e in result.get('repairs', [])),
             'repair_failed': sum(e.get('outcome') in ['validation_failure', 'api_failure'] for e in result.get('repairs', [])),
             'repair_skipped': sum(str(e.get('outcome', '')).startswith('skipped_') for e in result.get('repairs', [])),
             'quote_diagnostic_events': sum(bool(e.get('quote_diagnostics')) for e in result.get('repairs', [])),
             'provider_reported_cost_known_sum_usd': sum(reported) if reported else None,
             'provider_reported_cost_calls': len(reported),
             'gold_status': r['gold']['status'], 'status': prediction['status'],
             'strict_status_correct': prediction['status'] == r['gold']['status'], 'actions': len(prediction['actions']),
             'quote_exact': result.get('quotes_exact'), 'model_error': result.get('model_error'),
             'repairs': len([e for e in result.get('repairs', []) if e.get('attempted')]),
             'sources_read': len(result.get('reads', [])), 'read_failures': len(result.get('read_failures', [])),
             'validation_errors': len(result.get('engineering_errors', [])), 'semantic_review': 'pending; see semantic_review.csv',
             'raw_trace_file': 'rows.jsonl'}
        cases.append(p); indexed[key(r)] = p
    by_arm = {}
    for arm in dict.fromkeys([r['arm'] for r in rows] + [c['arm'] for c in calls]):
        batch = [p for p in cases if p['arm'] == arm]; ts = [t for t in turns if t['arm'] == arm]
        orphan = [c for c in calls if c['arm'] == arm and key(c) not in indexed]
        known = [t['estimated_cost_usd'] for t in ts if t['estimated_cost_usd'] is not None]
        reported = [t['provider_reported_cost_usd'] for t in ts if t['provider_reported_cost_usd'] is not None]
        billed = [t['billed_cost_usd'] for t in ts if t['billed_cost_usd'] is not None]
        retry = [t for t in ts if t['is_validation_repair']]
        retry_billed = [t['billed_cost_usd'] for t in retry if t['billed_cost_usd'] is not None]
        by_arm[arm] = {'completed_cases': len(batch), 'calls': len(ts), 'calls_without_completed_case': len(orphan),
                       'case_wall_ms': distribution([p['wall_ms'] for p in batch]),
                       'call_wall_ms': distribution([t['wall_ms'] for t in ts]),
                       'openrouter_latency_ms': distribution([t['openrouter_latency_ms'] for t in ts]),
                       'openrouter_generation_time_ms': distribution([t['openrouter_generation_time_ms'] for t in ts]),
                       'known_billed_cost_usd': sum(billed), 'unknown_billed_cost_calls': len(ts) - len(billed),
                       'billed_cost_complete': len(billed) == len(ts) and not orphan and meta['mode'] != 'scripted engineering',
                       'complete_case_billed_cost_usd': distribution([p['billed_cost_usd'] for p in batch]),
                       'repair_calls': len(retry), 'repair_wall_ms_total': sum(t['wall_ms'] or 0 for t in retry),
                       'known_repair_billed_cost_usd': sum(retry_billed), 'unknown_repair_billed_cost_calls': len(retry) - len(retry_billed),
                       'repair_validated_events': sum(p['repair_validated'] for p in batch),
                       'repair_failed_events': sum(p['repair_failed'] for p in batch),
                       'repair_skipped_events': sum(p['repair_skipped'] for p in batch),
                       'calls_per_case': distribution([p['calls'] for p in batch]),
                       'end_to_end_output_tokens_per_second': distribution([t['output_tokens_per_second_end_to_end'] for t in ts]),
                       'input_tokens_known_sum': sum(t['input_tokens'] or 0 for t in ts),
                       'output_tokens_known_sum': sum(t['output_tokens'] or 0 for t in ts),
                       'unknown_input_token_calls': sum(t['input_tokens'] is None for t in ts),
                       'unknown_output_token_calls': sum(t['output_tokens'] is None for t in ts),
                       'known_estimated_cost_usd': sum(known), 'unknown_cost_calls': len(ts) - len(known),
                       'cost_complete': len(known) == len(ts) and not orphan and meta['mode'] != 'scripted engineering',
                       'complete_case_cost_usd': distribution([p['estimated_cost_usd'] for p in batch]),
                       'provider_reported_cost_known_sum_usd': sum(reported) if reported else None,
                       'provider_reported_cost_calls': len(reported), 'repair_cases': sum(p['repairs'] > 0 for p in batch),
                       'model_error_cases': sum(bool(p['model_error']) for p in batch),
                       'resolved_models': sorted({t['resolved_model'] for t in ts if t['resolved_model']}),
                       'finish_reasons': {v: sum(t['finish_reason'] == v for t in ts) for v in sorted({t['finish_reason'] for t in ts if t['finish_reason']})}}
    robustness = []
    if config.get('phase') == 'model_benchmark':
        expected = {a['id'] for a in config['arms']}
        by_case = defaultdict(list)
        for p in cases: by_case[(p['case_id'], p['trial'])].append(p)
        for (cid, trial), batch in sorted(by_case.items()):
            signatures = {(p['status'], p['actions']) for p in batch}
            complete = {p['arm'] for p in batch} == expected
            robustness.append({'case_id': cid, 'trial': trial, 'models_observed': len(batch), 'complete': complete,
                               'status_count_agreement': complete and len(signatures) == 1,
                               'all_strict_status_correct': complete and all(p['strict_status_correct'] for p in batch),
                               'outcomes_json': json.dumps({p['arm']: {'status': p['status'], 'actions': p['actions'],
                                                           'strict_status_correct': p['strict_status_correct'],
                                                           'wall_ms': p['wall_ms'], 'estimated_cost_usd': p['estimated_cost_usd']}
                                                           for p in batch}),
                               'case_wall_ms_range': [min(p['wall_ms'] for p in batch), max(p['wall_ms'] for p in batch)],
                               'semantic_agreement': None})
    result = {'scope': meta['mode'], 'run_complete': meta['complete'], 'by_arm': by_arm,
              'cross_model_case_robustness': robustness, 'actual_consumption_reconciliation': billing,
              'notes': ['P95 uses linear interpolation; small samples remain descriptive.',
                        'Call time includes network, queueing, inference and response transfer; TTFT is unavailable.',
                        'Output tokens per second is end-to-end, not decode throughput; reasoning tokens may be included.',
                        'Cost estimates use declared prices; provider-reported cost is separately preserved, not audited billing.',
                        'Known cost subtotals do not turn missing/failed usage into zero cost.',
                        'Status/count agreement does not establish semantic agreement or correctness.']}
    (folder / 'operations.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    write_csv(folder / 'case_metrics.csv', cases); write_csv(folder / 'turn_metrics.csv', turns)
    write_csv(folder / 'cross_model_cases.csv', robustness)
    return result
