"""Two-stage experiment design; never calls models or chooses a winner silently."""
import hashlib
import json
from pathlib import Path

CANDIDATES = [
    ('m01', 'openai/gpt-6-luna', 'OpenAI', 'low'),
    ('m02', 'z-ai/glm-5.3-flash', 'Z.ai', 'low'),
    ('m03', 'google/gemini-3.5-flash-lite', 'Google', 'low'),
    ('m04', 'google/gemini-3.8-flash', 'Google', 'middle'),
    ('m05', 'openai/gpt-6.1-sol', 'OpenAI', 'middle'),
    ('m06', 'anthropic/claude-sonnet-5.5', 'Anthropic', 'middle'),
]


def stage1_config(catalog):
    available = {m['id']: m for m in catalog['models']}
    models = {}
    for key, mid, family, tier in CANDIDATES:
        entry = available[mid]; pricing = entry['pricing']
        models[key] = {'id': mid, 'family': family, 'price_tier': tier,
                       'input_usd_per_million': float(pricing['prompt']) * 1e6,
                       'output_usd_per_million': float(pricing['completion']) * 1e6,
                       'request_usd': float(pricing.get('request', 0)),
                       'price_source': catalog['source'], 'verified_utc': catalog['retrieved_utc'],
                       'catalog_created_unix': entry.get('created'),
                       'model_page': 'https://openrouter.ai/' + mid,
                       'supported_parameters': entry.get('supported_parameters', [])}
    return {'protocol_version': '2.0', 'phase': 'model_benchmark', 'schedule': 'case_round_robin',
            'purpose': 'Select suitable model backbones for an agent-focused mechanism study using the same frozen full workflow.',
            'models': models, 'budget_usd': 10.0, 'max_calls_per_email': 80,
            'authorization_status': 'proposal only; budget expansion requires owner authorization',
            'arms': [{'id': f'full_{key}', 'mode': 'full', 'selector': 'all', 'trials': 1,
                      'model': key, 'layer': 'model_benchmark'} for key in models],
            'stability_ids': ['N01', 'A23', 'A16', 'C11', 'E01', 'S01', 'S02', 'S08'],
            'selection_policy': {'select_count': [2, 3], 'quality_thresholds': {'action_precision': 0.9, 'action_recall': 0.9},
               'roles': ['quality leader', 'cheapest quality-eligible model', 'optional informative family/price contrast'],
               'tie_break': ['semantic correctness and task omissions when reviewed', 'strict status/count quality',
                             'model/validation failures', 'measured cost', 'latency'],
               'semantic_requirement': 'Classification cannot establish semantic task correctness. Pending review stays pending.',
               'no_eligible_rule': 'Report the failure; do not lower thresholds or relabel. Explicitly justify diagnostic model selection.'},
            'decoding_note': 'Same frozen API request/output cap; parameter support and provider reasoning defaults may differ.'}


def screening(run):
    run = Path(run)
    meta = json.loads((run / 'run.json').read_text(encoding='utf-8'))
    config = json.loads((run / 'config.json').read_text(encoding='utf-8'))
    summary = json.loads((run / 'summary.json').read_text(encoding='utf-8'))
    if config.get('phase') != 'model_benchmark':
        raise ValueError('Expected a stage-one full-workflow benchmark run')
    semantic = json.loads((run / 'semantic_summary.json').read_text(encoding='utf-8')) if (run / 'semantic_summary.json').exists() else None
    candidates = []
    for arm in config['arms']:
        m = summary['arms'].get(arm['id'])
        if not m:
            continue
        cost = summary['cost_by_arm'][arm['id']]
        candidates.append({'key': arm['model'], 'model': config['models'][arm['model']], 'metrics': m,
                           'cost': cost, 'semantic': semantic['arms'].get(arm['id']) if semantic else None,
                           'classification_eligible': (m['action_precision'] is not None and m['action_precision'] >= 0.9
                             and m['action_recall'] is not None and m['action_recall'] >= 0.9
                             and m['model_errors'] == 0 and m['quote_exact_cases'] == m['analyses'])})
    return {'phase': 'screening, not final model ranking', 'run_complete': meta['complete'],
            'semantic_review_complete': bool(semantic and semantic['complete']), 'candidates': candidates,
            'selection_policy': config['selection_policy'],
            'warning': 'One trial per case measures this run; repeatability is deferred to stage two. Review/error cases and unknown billing require inspection.'}


def stage2_config(run, selected, reason):
    run = Path(run).resolve()
    if len(selected) not in [2, 3] or len(set(selected)) != len(selected):
        raise ValueError('Choose exactly two or three distinct model keys')
    if not reason.strip():
        raise ValueError('Record the model-selection reason before ablation results')
    meta = json.loads((run / 'run.json').read_text(encoding='utf-8'))
    config = json.loads((run / 'config.json').read_text(encoding='utf-8'))
    if not meta['complete'] or config.get('phase') != 'model_benchmark':
        raise ValueError('Finish the full stage-one benchmark before generating stage two')
    if set(selected) - set(config['models']):
        raise ValueError('Selected model was not in stage one')
    packet = screening(run)
    candidate_keys = {c['key'] for c in packet['candidates'] if c['metrics']['analyses'] == 60}
    if set(selected) - candidate_keys:
        raise ValueError('Each selected model needs the full 60-case stage-one result')
    models = {key: config['models'][key] for key in selected}
    arms = []
    for key in selected:
        reference = f'full_{key}'
        for mode, selector, trials, layer in [('full', 'all', 1, 'reference'), ('prompt_only', 'all', 1, 'baseline'),
             ('no_thread', 'thread', 1, 'ablation'), ('no_external', 'external', 1, 'ablation'),
             ('read_all', 'external', 1, 'ablation'), ('no_repair', 'all', 1, 'ablation'),
             ('full', 'stability', 3, 'repeatability')]:
            aid = f'{mode}_{key}' if layer != 'repeatability' else f'stability_{key}'
            arm = {'id': aid, 'mode': mode, 'selector': selector, 'trials': trials, 'model': key, 'layer': layer}
            if layer in ['ablation', 'baseline']:
                arm['comparator'] = reference
            arms.append(arm)
    return {'protocol_version': '2.0', 'phase': 'selected_model_ablation', 'schedule': 'case_round_robin',
            'models': models, 'arms': arms, 'stability_ids': config['stability_ids'],
            'budget_usd': 10.0, 'max_calls_per_email': config['max_calls_per_email'],
            'authorization_status': 'generated design; reprice/review budget before paid execution',
            'required_bundle_sha256': meta['bundle_sha256'],
            'selection': {'models': selected, 'reason': reason, 'source_run': str(run),
                          'source_run_sha256': hashlib.sha256((run / 'run.json').read_bytes()).hexdigest(),
                          'semantic_review_complete_at_selection': packet['semantic_review_complete'],
                          'classification_eligibility': {c['key']: c['classification_eligible'] for c in packet['candidates']}},
            'comparator_policy': 'Fresh full-workflow reference per selected model in stage two; stage-one scores not merged as new trials.'}
