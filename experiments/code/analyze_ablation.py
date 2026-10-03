"""Update the single human report from completed ablation logs; no inference."""
from pathlib import Path
import json
root = Path(__file__).resolve().parent.parent
folder = root / 'results/ablation'

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))
summary = read(folder / 'summary.json')
operations = read(folder / 'operations.json')
config = read(folder / 'config.json')
meta = read(folder / 'run.json')
billing = read(folder / 'billing.json')
rows = [json.loads(x) for x in (folder / 'rows.jsonl').read_text(encoding='utf-8').splitlines()]
calls = [json.loads(x) for x in (folder / 'calls.jsonl').read_text(encoding='utf-8').splitlines()]
from pipeline import scheduled_tasks, jsonl
expected = {(a['id'], c['case_id'], t) for a, c, t in scheduled_tasks(config, jsonl(root / 'data/frozen-core/dataset.jsonl'), None)}
observed = {(r['arm'], r['case_id'], r['trial']) for r in rows}
assert meta['complete'] and len(rows) == 500 and (len(observed) == 500) and (observed == expected)
assert billing['reconciled'] and billing['generation_cost_calls'] == 579
global_bill = read(folder / 'global-billing.json')
if 'snapshot_at_inference_end' not in global_bill:
    global_bill['snapshot_at_inference_end'] = global_bill['after']
global_bill['after'] = billing['after']
global_bill['actual_counter_delta_usd'] = billing['after']['key_usage_usd'] - global_bill['baseline']['key_usage_usd']
global_bill['updated_from'] = 'Final settled ablation billing audit; replaces provisional inference-end counter.'
(folder / 'global-billing.json').write_text(json.dumps(global_bill, indent=2) + '\n', encoding='utf-8')
names = {'m01': 'GPT-6 Luna', 'm06': 'Claude Sonnet 5.5'}
modes = [('full', 'Full workflow'), ('prompt_only', 'One-call prompt baseline'), ('no_thread', 'No thread history'), ('no_external', 'No external reading'), ('read_all', 'Read all sources'), ('no_repair', 'No model repair'), ('stability', 'Repeated trials')]
lines = ['## 11. Completed two-model ablations', '', 'Completed at 08:56 Singapore time on 2026-10-03: Luna and Sonnet each completed 250 analyses, 500/500 total, with 579 requests. The measured core, prompts, parser and interface settings were unchanged; forced JSON was not introduced. Semantic review is pending.', '', f"Actual ablation charges: **{billing['key_usage_delta_usd']:.7f} USD**, with 579/579 generation bills matching usage counters. Cumulative benchmark/ablation spend: **{global_bill['actual_counter_delta_usd']:.7f} USD**; remaining under USD 5: **{5 - global_bill['actual_counter_delta_usd']:.7f} USD**. Initially unsettled counters were updated after final reconciliation; token estimates are not actual fees. The missing benchmark bill limitation remains.", '', '### Full condition table', '', 'Scores here are strict status matches, not full semantic quality. Denominators differ; mechanism comparisons use identical case IDs below. Twenty-four repeat observations are eight cases times three, not independent cases.', '', '| Condition | Luna strict status | Luna P50 seconds / actual USD | Sonnet strict status | Sonnet P50 seconds / actual USD |', '| --- | ---: | ---: | ---: | ---: |']
for mode, label in modes:
    values = []
    for key in names:
        arm = f'{mode}_{key}'
        m = summary['arms'][arm]
        o = operations['by_arm'][arm]
        values.extend([f"{m['strict_status_match']}/{m['analyses']}", f"{o['case_wall_ms']['p50'] / 1000:.2f} / {o['known_billed_cost_usd']:.6f}"])
    lines.append('| ' + label + ' | ' + ' | '.join(values) + ' |')
lines += ['', '### Paired case comparisons', '', 'Each full comparator uses only IDs shared with its ablation. Do not compare twelve/seventeen-case conditions directly with sixty full cases. Fees also use common cases.', '', '| Model | Removed/replaced factor | Full correct | Condition correct | Full / condition cost, USD |', '| --- | --- | ---: | ---: | ---: |']
changes = []
case_metrics = {}
import csv
with (folder / 'case_metrics.csv').open(encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f):
        case_metrics[r['arm'], r['case_id'], int(r['trial'])] = r
for key, name in names.items():
    for mode, label in modes[1:-1]:
        arm = f'{mode}_{key}'
        pair = summary['paired_comparisons'][arm]
        n = pair['paired_analyses']
        selected = {r['case_id'] for r in rows if r['arm'] == arm}
        ref = f'full_{key}'

        def cost(a):
            return sum((float(r.get('billed_cost_usd') or 0) for (ar, c, t), r in case_metrics.items() if ar == a and c in selected and (t == 1)))
        lines.append(f"| {name} | {label} | {pair['comparator_metrics']['strict_status_match']}/{n} | {pair['arm']['strict_status_match']}/{n} | {cost(ref):.6f} / {cost(arm):.6f} |")
        reference = {r['case_id']: r for r in rows if r['arm'] == ref}
        for r in rows:
            if r['arm'] != arm:
                continue
            f = reference[r['case_id']]
            gold = r['gold']['status']
            a = f['result']['prediction']['status']
            b = r['result']['prediction']['status']
            if a != b:
                changes.append({'model': name, 'condition': label, 'case_id': r['case_id'], 'gold': gold, 'full': a, 'condition_status': b, 'full_reason': f['result']['prediction']['reason'], 'condition_reason': r['result']['prediction']['reason']})
(folder / 'paired_status_changes.json').write_text(json.dumps(changes, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
lines += ['', '### Supported mechanism conclusions and limits', '', '**External reading has the clearest effect.** On seventeen shared cases, Luna drops 16/17 to 3/17 and Sonnet 17/17 to 3/17. Both review 16/17 without reading, often safely rather than guessing missing tasks. Body text cannot replace attachments/links; delivery falls while safe fallback persists.', '', '**Threads matter across families.** On twelve shared cases both full workflows score 11/12 and no-thread 9/12. Luna reviews C02/C09 without context; Sonnet reviews C10 and acts on C13 that should be reviewed. Different cases fail; a two-point loss alone is incomplete.', '', '**One-call prompting is insufficient.** Both score 44/60 versus full 58/60 and 59/60. Reading, repair and segment merging are removed together, so the 14/15-point losses cannot be attributed to one component.', '', '**Similar read-all scores do not remove planning value.** Luna full/read-all both score 16/17, but fail E07 format versus irrelevant corrupt S07 material. Sonnet declines 17/17 to 16/17 on S07. Planning avoids irrelevant broken sources; read-all saves a planning call. Report quality, fault exposure and fee tradeoffs.', '', '**Repair does not consistently improve aggregate scores.** Luna full/no-repair score 58/60 and 59/60; Sonnet 59/60 and 58/60. Independent requests vary in format/judgment; this is neither harmful Luna repair nor guaranteed Sonnet benefit. Sonnet C10 changes interpretation without repair. Luna full E07 fails before/after repair, while a separate no-repair first answer is valid. Use events/evidence/failure chains; fixed-first-answer replay can isolate causality.', '', '**Original-source repair genuinely triggered.** Luna full attempted C12 missing-evidence repair successfully, E07 format unsuccessfully and S02 quote successfully. S02 similarity 0.994 concealed the critical $25k-$50 versus $25k-$50k difference; it was not auto-approved, and regeneration passed validation. Sonnet repaired C12 quotes. Validation success does not establish completed semantic review.', '', '**Selected repeats are stable, not universally representative.** Eight selected cases repeated three times per model form sixteen groups with identical status/count. Strict score is 21/24 per model, losing only C11 alternative-label points; permitted scores are 24/24. Wording/kind/semantic equivalence and universal stability are not established.', '', 'Fresh full versus benchmark differs: Luna 59/60 then 58/60; Sonnet 58/60 then 59/60. The earlier one-point gap is not a definitive ranking.', '', '### Raw key-failure responses', '', 'Luna full E07 call 1 is a valid plan. Extraction/repair calls 2/3 report Extra data: an extra double quote and right brace follow a complete JSON object. Trailing text causes rejection. Format failure is not confined to Gemini. The examples are verbatim final response content, not reasoning.']
for c in calls:
    if c['arm'] == 'full_m01' and c['case_id'] == 'E07':
        content = ((c.get('transport') or {}).get('response_json') or {}).get('choices', [{}])[0].get('message', {}).get('content')
        lines += ['', f"Call {c['call']}:", '', '````text', content or 'null', '````']
lines += ['', 'Results/bills: `results/ablation/`; paired changes: `paired_status_changes.json`. Exhaustive semantic review, independent tests and forced JSON remain future work. No inference process is running.']
p = root / 'REPORT.md'
s = p.read_text(encoding='utf-8')
marker = '\n## 11.'
semantic_tail = '\n## 12.' + s.split('\n## 12.', 1)[1] if '\n## 12.' in s else ''
if (folder / 'semantic_summary.json').exists() and read(folder / 'semantic_summary.json').get('complete'):
    lines = [line.replace('Semantic review is pending.', 'All 500 ablation outputs received Codex AI semantic review in section 12, not independent human review.').replace('Exhaustive semantic review, independent tests and forced JSON remain future work.', 'Section 12 reviews ablations; exhaustive 360-output benchmark review, independent tests and forced JSON remain future work.') for line in lines]
s = s.split(marker)[0] + '\n' + '\n'.join(lines) + '\n' + semantic_tail
p.write_text(s, encoding='utf-8')
for name in ['README.md', 'PROTOCOL.md']:
    p = root / name
    s = p.read_text(encoding='utf-8')
    s = s.replace('500 ablation analyses are running', '500 ablation analyses are complete').replace('Experiment 2: mechanism ablations (running)', 'Experiment 2: completed mechanism ablations')
    s = s.replace('Luna and Sonnet each started 250 analyses, 500 total.', 'Luna and Sonnet each completed 250 analyses, 500 total; 579 bills reconcile. No model calls are running.')
    s = s.replace('Cumulative charges are USD 1.344801303 under USD 5.', 'Benchmark/ablation charges total USD 3.224528503 under USD 5.')
    s = s.replace('Benchmark cost: USD 1.344801303; remaining: USD 3.655198697.', 'Benchmark USD 1.344801303; ablations USD 1.879727200; total USD 3.224528503; remaining USD 1.775471497.')
    p.write_text(s, encoding='utf-8')
print('Verified canonical 500 observations and 579 bills; updated sole report. Actual global USD:', global_bill['actual_counter_delta_usd'])
