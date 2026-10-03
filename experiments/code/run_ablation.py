"""Canonical stage-two runner with global actual-spend accounting and resumable rows.

Uses existing task scheduling, frozen core, transport, adapters and scoring.
Per-analysis reservations are released between cases; uncertain charges stay held.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, sys, time
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parent
EXPERIMENTS=ROOT.parent
sys.path.insert(0,str(ROOT))
import pipeline, design
from billing import Accounting

def now(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v): p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def append(p,v):
    with p.open('a',encoding='utf-8') as f: f.write(json.dumps(v,ensure_ascii=False)+'\n')

for line in (EXPERIMENTS/'.env').read_text(encoding='utf-8-sig').splitlines():
    line=line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    name,value=line.split('=',1); name=name.strip(); value=value.strip()
    if len(value)>1 and value[0]==value[-1] and value[0] in ['"',"'"]: value=value[1:-1]
    if name in ['OPENROUTER_API_KEY','OPENROUTER_MANAGEMENT_KEY']: os.environ[name]=value

bundle=EXPERIMENTS/'data/frozen-core'
benchmark=EXPERIMENTS/'results/model-benchmark'
output=EXPERIMENTS/'results/ablation'
baseline=pipeline.read(benchmark/'billing-baseline.json')
cap=5.0
accounting=Accounting(os.environ['OPENROUTER_API_KEY'],os.getenv('OPENROUTER_MANAGEMENT_KEY'))
snapshot=accounting.snapshot()
if snapshot.get('key_usage_usd') is None: raise SystemExit('Actual usage unavailable; no inference started')
initial_spend=snapshot['key_usage_usd']-baseline['key_usage_usd']
if initial_spend<0 or initial_spend>=cap: raise SystemExit('Global budget unavailable; no inference started')

reason=('Owner explicitly selected GPT-6 Luna and Claude Sonnet 5.5 and authorized immediate ablation. '
        'Both meet predeclared classification thresholds. Cross-family low-cost versus quality contrast; '
        'semantic review remains pending and is not relabelled complete. No JSON-mode upgrade in this protocol.')
config=design.stage2_config(benchmark,['m01','m06'],reason)
with urlopen(Request('https://openrouter.ai/api/v1/models',headers={'Accept':'application/json'}),timeout=15) as response:
    catalog=json.load(response)
catalog_map={m['id']:m for m in catalog['data']}
for model in config['models'].values():
    live=catalog_map.get(model['id'])
    if not live: raise SystemExit('Chosen model unavailable; no inference started')
    prices=live['pricing']
    for field,price_key,mult in [('input_usd_per_million','prompt',1e6),('output_usd_per_million','completion',1e6),('request_usd','request',1)]:
        current=float(prices.get(price_key,0))*mult
        if abs(current-model[field])>1e-9: raise SystemExit('Frozen model price changed; inspect before inference')
config.update(budget_usd=cap-initial_spend,total_experiment_spend_limit_usd=cap,
    authorization_status='Owner authorized on 2026-10-03; all phases cumulatively <= USD 5',
    accounting_policy='Actual counter delta from original stage-one baseline; unreconciled requests held conservatively. Per-analysis upper reservations never used as actual costs.',
    global_billing_baseline=baseline,spend_before_stage_two_usd=initial_spend)
pipeline.verify_bundle(bundle)
queue=pipeline.scheduled_tasks(config,pipeline.jsonl(bundle/'dataset.jsonl'),None)
if len(queue)!=500: raise SystemExit('Unexpected canonical matrix; no inference started')
stage1_meta=pipeline.read(benchmark/'run.json')
for name in ['engine.py','telemetry.py']:
    if sha(ROOT/name)!=stage1_meta['experiment_code'][name]: raise SystemExit('Scientific adapter/transport changed; stop')
pipeline.activate(bundle)
from engine import execute, Meter
from telemetry import ObservedAPIClient
from scoring import score_run

output.mkdir(exist_ok=False)
dump(output/'config.json',config)
dump(output/'billing-baseline.json',snapshot)
dump(output/'global-billing-baseline.json',baseline)
dump(ROOT/'configs/ablation.json',config)
code_hashes={p.name:sha(p) for p in ROOT.glob('*.py')}
meta={'started_utc':now(),'bundle':str(bundle),'bundle_sha256':sha(bundle/'manifest.json'),
    'experiment_code':code_hashes,'config_sha256':sha(output/'config.json'),'mode':'live',
    'planned_analyses':len(queue),'complete':False,'budget_usd':config['budget_usd'],
    'paid_calls':0,'measured_usd':0.0,'reserved_usd':0.0,'unknown_usage_calls':0,
    'source_benchmark':str(benchmark),'global_total_cap_usd':cap,'status':'running',
    'reservation_policy':'Original frozen Meter per analysis, remaining global actual-spend cap. Full reservation held within an analysis; unused reservation released afterward.',
    'prompt_parser_transport':'Same as stage-one. API JSON mode is deferred to separately versioned upgrade.'}
dump(output/'run.json',meta)
(output/'rows.jsonl').touch()
recorded_cost=0.0
unknown_held=0.0025667  # Previously interrupted request with no response; preserve conservative hold.
complete_rows=[]
all_calls=[]
active_meter=None
try:
    for arm,case,trial in queue:
        current=accounting.snapshot()
        if current.get('key_usage_usd') is None: raise RuntimeError('Actual-spend counter unavailable; stopped')
        counter=current['key_usage_usd']-baseline['key_usage_usd']
        spent=max(counter,initial_spend+recorded_cost)+unknown_held
        remaining=cap-spent
        if remaining<=0: raise RuntimeError('Global USD 5 actual/held cap reached')
        active_meter=Meter(remaining,output/'calls.jsonl')
        spec=config['models'][arm['model']]
        client=active_meter.client(ObservedAPIClient('https://openrouter.ai/api/v1/chat/completions',
            os.environ['OPENROUTER_API_KEY'],spec['id'],accounting=accounting),spec,
            config['max_calls_per_email'],arm['id'],case['case_id'],trial)
        started_utc=now()
        append(output/'events.jsonl',{'event':'case_started','arm':arm['id'],'case_id':case['case_id'],'trial':trial,'started_utc':started_utc})
        started=time.perf_counter(); audit_start=accounting.audit_wall_ms
        result=execute(arm['mode'],case,client)
        elapsed=(time.perf_counter()-started)*1000; audit_ms=accounting.audit_wall_ms-audit_start
        row={'arm':arm['id'],'trial':trial,'case_id':case['case_id'],'started_utc':started_utc,'ended_utc':now(),
            'category':case['category'],'origin':case['origin'],'gold':case['gold'],
            'accepted_outcomes':case['accepted_outcomes'],'result':result,
            'wall_ms':max(0,elapsed-audit_ms),'wall_with_accounting_ms':elapsed,'accounting_wall_ms':audit_ms,'semantic_review':None}
        append(output/'rows.jsonl',row); complete_rows.append(row)
        append(output/'events.jsonl',{'event':'case_completed','arm':arm['id'],'case_id':case['case_id'],'trial':trial,'ended_utc':row['ended_utc']})
        new_calls=pipeline.jsonl(output/'calls.jsonl')[len(all_calls):]
        all_calls.extend(new_calls)
        for call in new_calls:
            raw=(call.get('transport') or {}).get('response_json') or {}
            cost=(raw.get('usage') or {}).get('cost')
            if isinstance(cost,(int,float)): recorded_cost+=cost
            else: unknown_held+=call['reservation_usd']
        meta.update(completed_analyses=len(complete_rows),paid_calls=len(all_calls),
            measured_usd=meta['measured_usd']+active_meter.measured,
            reserved_usd=meta['reserved_usd']+active_meter.reserved,
            unknown_usage_calls=meta['unknown_usage_calls']+active_meter.unknown_usage_calls)
        active_meter=None
        dump(output/'run.json',meta)
        dump(output/'progress.json',{'updated_utc':now(),'completed':len(complete_rows),'expected':len(queue),
            'actual_counter_spend_usd_before_case':counter,'known_response_cost_stage_two_usd':recorded_cost,
            'unknown_held_usd':unknown_held,'global_total_cap_usd':cap,'last_completed':{'arm':arm['id'],'case_id':case['case_id'],'trial':trial}})
        if len(complete_rows)%20==0: print(f'Ablation {len(complete_rows)}/500; global actual/held before case USD {spent:.6f}.',flush=True)
    meta.update(complete=True,status='inference_complete_billing_pending')
except BaseException as exc:
    meta.update(status='stopped',stop_reason=type(exc).__name__+': '+str(exc))
    raise
finally:
    # Even interrupted calls and completed rows remain saved for exact-pair resume.
    if active_meter is not None:
        meta['measured_usd']+=active_meter.measured; meta['reserved_usd']+=active_meter.reserved
        meta['unknown_usage_calls']+=active_meter.unknown_usage_calls
    all_calls=pipeline.jsonl(output/'calls.jsonl') if (output/'calls.jsonl').exists() else []
    meta.update(ended_utc=now(),paid_calls=len(all_calls),
        experiment_code_unchanged=code_hashes=={p.name:sha(p) for p in ROOT.glob('*.py')})
    dump(output/'run.json',meta)
    after=accounting.snapshot()
    dump(output/'global-billing.json',{'baseline':baseline,'after':after,
        'actual_counter_delta_usd':after['key_usage_usd']-baseline['key_usage_usd'] if after.get('key_usage_usd') is not None else None,
        'global_total_cap_usd':cap,'unknown_held_usd':unknown_held})
    score_run(output)

accounting.reconcile(output,snapshot,all_calls)
score_run(output)
meta.update(status='complete',ended_utc=now()); dump(output/'run.json',meta)
print('Ablation complete: 500/500. Results saved; main REPORT.md remains the sole report.',flush=True)
