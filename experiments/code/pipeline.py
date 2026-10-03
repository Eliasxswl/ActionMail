"""Independent experiment CLI. Imports only an explicitly frozen ActionMail core."""
import argparse
import base64
import csv
import hashlib
import importlib.metadata
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def file_hashes(folder):
    return {p.relative_to(folder).as_posix(): digest(p.read_bytes())
            for p in sorted(folder.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def verify_bundle(bundle):
    bundle = Path(bundle).resolve()
    manifest = read(bundle / 'manifest.json')
    for relative, expected in manifest['files'].items():
        path = (bundle / relative).resolve()
        if not path.is_relative_to(bundle) or digest(path.read_bytes()) != expected:
            raise ValueError(f'Bundle integrity failure: {relative}')
    # No unexpected executable source may enter the frozen import tree.
    actual = {p.relative_to(bundle).as_posix() for p in (bundle / 'runtime').rglob('*.py')}
    expected = {p for p in manifest['files'] if p.startswith('runtime/') and p.endswith('.py')}
    if actual != expected:
        raise ValueError('Unexpected or missing frozen Python module')
    return bundle, manifest


def activate(bundle):
    # A CLI invocation is a fresh interpreter; refuse accidental live-core reuse.
    if any(k == 'actionmail' or k.startswith('actionmail.') for k in sys.modules):
        raise RuntimeError('Use a fresh process; an ActionMail package is already imported')
    sys.path.insert(0, str(Path(bundle) / 'runtime'))


def prepare(source, output):
    source = Path(source).resolve()
    output = Path(output).resolve()
    if output == source or output.is_relative_to(source):
        raise ValueError('Bundle must be outside the live ActionMail repository')
    output.mkdir(parents=True, exist_ok=False)
    src = source / 'src'
    before = {p.relative_to(src).as_posix(): digest(p.read_bytes()) for p in sorted(src.rglob('*.py'))}
    if not before or 'actionmail/workflow/multi_pipeline.py' not in before:
        raise ValueError('ActionMail source not found')
    for relative in before:
        destination = output / 'runtime' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((src / relative).read_bytes())
    copied = {p.relative_to(output / 'runtime').as_posix(): digest(p.read_bytes())
              for p in (output / 'runtime').rglob('*.py')}
    after = {p.relative_to(src).as_posix(): digest(p.read_bytes()) for p in sorted(src.rglob('*.py'))}
    if before != copied or before != after:
        raise ValueError('Source changed during snapshot; discard incomplete bundle and prepare a fresh one')
    # Decode using the frozen core, never the concurrently edited package.
    activate(output)
    from actionmail.evaluation.suite import load_suite
    from actionmail.application.store import encode_email
    eval_before = file_hashes(source / 'evaluation')
    cases = load_suite(source / 'evaluation/active_suite.json', source.parent / 'data')
    normalized = []
    for case in cases:
        normalized.append({'case_id': case.case_id, 'category': case.record['category'],
                           'origin': case.record['source']['kind'], 'email': encode_email(case.email),
                           'gold': case.gold, 'accepted_outcomes': case.record.get('accepted_outcomes', []),
                           'source_expectations': case.record.get('source_expectations', {}),
                           'source_sha256': case.source_hash,
                           'reference_note': case.record.get('annotation_note', '')})
    if eval_before != file_hashes(source / 'evaluation'):
        raise ValueError('Reference inputs changed during normalization; use a fresh bundle')
    # All selected email text, snapshots and attachment bytes are embedded: no live paths at run time.
    (output / 'dataset.jsonl').write_text('\n'.join(json.dumps(c, ensure_ascii=False) for c in normalized) + '\n', encoding='utf-8')
    originals = output / 'source_registry'
    originals.mkdir()
    for name in ['active_suite.json', 'cases.jsonl', 'supplement_v2_approved.jsonl', 'v2_reference_overrides.json']:
        (originals / name).write_bytes((source / 'evaluation' / name).read_bytes())
    try:
        head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        head = None
    try:
        pypdf = importlib.metadata.version('pypdf')
    except importlib.metadata.PackageNotFoundError:
        pypdf = None
    dump(output / 'manifest.json', {'format': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
         'git_head': head, 'source_hashes': before, 'reference_hashes': eval_before,
         'files': file_hashes(output), 'case_count': len(normalized), 'python': sys.version, 'pypdf': pypdf,
         'dataset_role': 'development/regression; reused for tuning; not held-out',
         'redistribution': 'Local public-derived emails and course corpus; check licenses before publishing bundle'})
    print(f'Prepared frozen core and {len(normalized)} self-contained cases: {output}')


def tasks(config, cases, selected=None):
    modes = {'rules', 'prompt_only', 'full', 'no_thread', 'no_external', 'read_all', 'no_repair'}
    selectors = {'all', 'thread', 'external', 'stability'}
    seen = set()
    for arm in config['arms']:
        if arm['id'] in seen or arm['mode'] not in modes or arm['selector'] not in selectors:
            raise ValueError('Duplicate arm or unknown experiment mode/selector')
        seen.add(arm['id'])
        if selected and arm['id'] not in selected:
            continue
        if not isinstance(arm['trials'], int) or arm['trials'] < 1:
            raise ValueError('Trials must be a positive integer')
        for case in cases:
            selector = arm['selector']
            include = (selector == 'all' or selector == 'thread' and bool(case['email']['thread'])
                       or selector == 'external' and bool(case['email']['external_sources'])
                       or selector == 'stability' and case['case_id'] in config['stability_ids'])
            if include:
                for trial in range(1, arm['trials'] + 1):
                    yield arm, case, trial
    if selected and set(selected) - seen:
        raise ValueError('Unknown selected arm')


def plan(bundle, config, arms):
    bundle, manifest = verify_bundle(bundle)
    if config.get('required_bundle_sha256') and config['required_bundle_sha256'] != digest((bundle / 'manifest.json').read_bytes()):
        raise ValueError('Stage-two bundle differs from the frozen stage-one bundle')
    cases = jsonl(bundle / 'dataset.jsonl')
    queue = scheduled_tasks(config, cases, arms)
    counts = {}
    for arm, _, _ in queue:
        counts[arm['id']] = counts.get(arm['id'], 0) + 1
    missing = sorted({arm.get('model') for arm, _, _ in queue if arm['mode'] != 'rules'
                      and not config['models'][arm['model']].get('id')})
    return {'bundle_sha256': digest((bundle / 'manifest.json').read_bytes()),
            'dataset_role': manifest['dataset_role'], 'analyses_by_arm': counts, 'total_analyses': len(queue),
            'unconfigured_models': missing, 'paid_calls': 0,
            'note': 'No inference. The template leaves prices unset; a proposed priced config does not authorize inference. Analysis count is not API-call count.'}


def run(bundle, config_path, output, arms, paid=False, scripted=False):
    bundle, manifest = verify_bundle(bundle)
    config = read(config_path)
    if config.get('required_bundle_sha256') and config['required_bundle_sha256'] != digest((bundle / 'manifest.json').read_bytes()):
        raise ValueError('Stage-two bundle differs from the frozen stage-one bundle')
    queue = scheduled_tasks(config, jsonl(bundle / 'dataset.jsonl'), arms)
    if not queue:
        raise ValueError('Empty experiment selection')
    needs_model = any(a['mode'] != 'rules' for a, _, _ in queue)
    if needs_model and not paid and not scripted:
        raise ValueError('Model arms require --approve-paid; use --scripted only for smoke fixtures')
    if scripted and manifest.get('dataset_role') != 'scripted engineering smoke; not model evaluation':
        raise ValueError('Scripted mode is restricted to the smoke bundle')
    if paid and scripted:
        raise ValueError('Paid and scripted modes are mutually exclusive')
    if not isinstance(config.get('budget_usd'), (int, float)) or config['budget_usd'] <= 0:
        raise ValueError('A positive run budget is required')
    if not isinstance(config.get('max_calls_per_email'), int) or config['max_calls_per_email'] < 1:
        raise ValueError('Positive per-email call limit required')
    if paid and needs_model:
        for a, _, _ in queue:
            if a['mode'] == 'rules':
                continue
            spec = config['models'][a['model']]
            if not spec.get('id') or any(not isinstance(spec.get(k), (int, float)) or spec[k] <= 0
                                        for k in ['input_usd_per_million', 'output_usd_per_million']):
                raise ValueError('Live model identifiers and verified positive token prices are required')
            if not isinstance(spec.get('request_usd'), (int, float)) or spec['request_usd'] < 0:
                raise ValueError('Verified non-negative request fee is required')
        if not os.getenv('OPENROUTER_API_KEY'):
            raise ValueError('OPENROUTER_API_KEY not configured')
    output = Path(output).resolve()
    if output == bundle or output.is_relative_to(bundle):
        raise ValueError('Run output must not modify the frozen bundle')
    output.mkdir(parents=True, exist_ok=False)
    activate(bundle)
    from engine import execute, Meter, Scripted
    from telemetry import ObservedAPIClient
    code_hashes = {p.name: digest(p.read_bytes()) for p in ROOT.glob('*.py')}
    dump(output / 'config.json', config)
    metadata = {'started_utc': datetime.now(timezone.utc).isoformat(), 'bundle': str(bundle),
                'bundle_sha256': digest((bundle / 'manifest.json').read_bytes()), 'experiment_code': code_hashes,
                'config_sha256': digest(Path(config_path).read_bytes()), 'selected_arms': arms,
                'mode': 'scripted engineering' if scripted else 'live' if needs_model else 'offline rules',
                'planned_analyses': len(queue), 'complete': False, 'budget_usd': config['budget_usd'],
                'observability': 'Per-case rows, per-call full request/response, lifecycle events and derived operational tables; non-streaming TTFT unavailable',
                'billing_note': 'Conservative token-byte reservations under declared prices; not provider billing enforcement.'}
    dump(output / 'run.json', metadata)
    meter = Meter(config['budget_usd'], output / 'calls.jsonl')
    accounting = None
    baseline = None
    try:
        if paid and needs_model:
            from billing import Accounting
            accounting = Accounting(os.environ['OPENROUTER_API_KEY'], os.getenv('OPENROUTER_MANAGEMENT_KEY'))
            baseline = accounting.snapshot()
            dump(output / 'billing-baseline.json', baseline)
            if baseline['key_usage_usd'] is None:
                raise ValueError('Cannot capture baseline actual usage; no paid inference started')
        with (output / 'rows.jsonl').open('x', encoding='utf-8') as f:
            for arm, case, trial in queue:
                case_started_utc = datetime.now(timezone.utc).isoformat()
                with (output / 'events.jsonl').open('a', encoding='utf-8') as events:
                    events.write(json.dumps({'event': 'case_started', 'arm': arm['id'], 'case_id': case['case_id'],
                                             'trial': trial, 'started_utc': case_started_utc}) + '\n')
                client = None
                if arm['mode'] != 'rules':
                    if scripted:
                        client = Scripted(case['scripted_responses'])
                    else:
                        spec = config['models'][arm['model']]
                        client = meter.client(ObservedAPIClient('https://openrouter.ai/api/v1/chat/completions',
                                  os.environ['OPENROUTER_API_KEY'], spec['id'], accounting=accounting), spec,
                                  config['max_calls_per_email'], arm['id'], case['case_id'], trial)
                started = time.perf_counter()
                audit_started = accounting.audit_wall_ms if accounting else 0
                result = execute(arm['mode'], case, client)
                elapsed_ms = (time.perf_counter() - started) * 1000
                audit_ms = accounting.audit_wall_ms - audit_started if accounting else 0
                row = {'arm': arm['id'], 'trial': trial, 'case_id': case['case_id'],
                       'started_utc': case_started_utc, 'ended_utc': datetime.now(timezone.utc).isoformat(),
                       'category': case['category'], 'origin': case['origin'], 'gold': case['gold'],
                       'accepted_outcomes': case['accepted_outcomes'], 'result': result,
                       'wall_ms': max(0, elapsed_ms - audit_ms), 'wall_with_accounting_ms': elapsed_ms,
                       'accounting_wall_ms': audit_ms,
                       'semantic_review': None}
                f.write(json.dumps(row, ensure_ascii=False) + '\n'); f.flush()
                with (output / 'events.jsonl').open('a', encoding='utf-8') as events:
                    events.write(json.dumps({'event': 'case_completed', 'arm': arm['id'], 'case_id': case['case_id'],
                                             'trial': trial, 'ended_utc': row['ended_utc']}) + '\n')
        metadata['complete'] = True
    finally:
        metadata.update(ended_utc=datetime.now(timezone.utc).isoformat(), reserved_usd=meter.reserved,
                        measured_usd=meter.measured, paid_calls=meter.calls,
                        unknown_usage_calls=meter.unknown_usage_calls,
                        experiment_code_unchanged=code_hashes == {p.name: digest(p.read_bytes()) for p in ROOT.glob('*.py')})
        dump(output / 'run.json', metadata)
        if accounting and baseline and baseline.get('key_usage_usd') is not None:
            accounting.reconcile(output, baseline, jsonl(output / 'calls.jsonl') if (output / 'calls.jsonl').exists() else [])
        if not (output / 'rows.jsonl').exists():
            (output / 'rows.jsonl').write_text('', encoding='utf-8')
        from scoring import score_run
        score_run(output)
    if not metadata['experiment_code_unchanged']:
        raise ValueError('Experiment source changed during execution; results are not a stable experiment')
    print(f'Completed {len(queue)} analyses: {output}')


def scheduled_tasks(config, cases, arms=None):
    queue = list(tasks(config, cases, arms))
    schedule = config.get('schedule', 'arm_order')
    if schedule == 'case_round_robin':
        case_order = {c['case_id']: i for i, c in enumerate(cases)}
        arm_order = {a['id']: i for i, a in enumerate(config['arms'])}
        queue.sort(key=lambda job: (case_order[job[1]['case_id']], job[2], arm_order[job[0]['id']]))
    elif schedule != 'arm_order':
        raise ValueError('Unknown execution schedule')
    return queue


def smoke(bundle):
    bundle, _ = verify_bundle(bundle)
    target = bundle.parent / (bundle.name + '-smoke')
    target.mkdir(parents=True, exist_ok=False)
    import shutil
    shutil.copytree(bundle / 'runtime', target / 'runtime', ignore=shutil.ignore_patterns('__pycache__'))
    original = jsonl(bundle / 'dataset.jsonl')[0]['email']
    fixtures = []
    for cid, body, status in [('SM01', 'Weekly update. Everything is on track.', 'no_action'),
                              ('SM02', 'Alex, please send the brief.', 'action'),
                              ('SM03', 'Alex, review the attached workbook. The workbook is missing.', 'needs_review')]:
        email = dict(original, case_id=cid, target_recipient='alex@example.com', sender='manager@example.com',
                     recipients=['alex@example.com'], to_recipients=['alex@example.com'], cc_recipients=[],
                     subject='Engineering smoke', body=body, thread=[], external_sources=[], read_sources=[],
                     unread_sources=[], received_at='2026-10-02T09:00:00+08:00', legacy_soft_wraps=False)
        reply = {'status': status, 'actions': [], 'reason': 'Authored scripted engineering response.',
                 'evidence': [{'source_id': 'body', 'quote': body}]}
        if status == 'action':
            reply['actions'] = [{'kind': 'perform_task', 'text': 'Send the brief.', 'deadline': None,
                                  'evidence': [{'source_id': 'body', 'quote': body}]}]
        fixtures.append({'case_id': cid, 'category': 'smoke', 'origin': 'authored_scripted', 'email': email,
                         'gold': reply, 'accepted_outcomes': [], 'scripted_responses': [json.dumps(reply)]})
    (target / 'dataset.jsonl').write_text('\n'.join(json.dumps(c) for c in fixtures) + '\n', encoding='utf-8')
    dump(target / 'manifest.json', {'format': 1, 'files': file_hashes(target), 'case_count': 3,
         'dataset_role': 'scripted engineering smoke; not model evaluation'})
    print(f'Smoke bundle: {target}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('prepare'); a.add_argument('--source', type=Path, default=ROOT.parent / 'ActionMail'); a.add_argument('--output', type=Path, required=True)
    for name in ['plan', 'run']:
        a = sub.add_parser(name); a.add_argument('--bundle', type=Path, required=True)
        a.add_argument('--config', type=Path, default=ROOT / 'configs/core.json'); a.add_argument('--arm', action='append')
        if name == 'run':
            a.add_argument('--output', type=Path, required=True); a.add_argument('--approve-paid', action='store_true'); a.add_argument('--scripted', action='store_true')
    a = sub.add_parser('smoke-bundle'); a.add_argument('--bundle', type=Path, required=True)
    a = sub.add_parser('score'); a.add_argument('--run', type=Path, required=True)
    a = sub.add_parser('review-score'); a.add_argument('--run', type=Path, required=True)
    a = sub.add_parser('mechanism'); a.add_argument('--bundle', type=Path, required=True); a.add_argument('--output', type=Path, required=True)
    a = sub.add_parser('inspect'); a.add_argument('--bundle', type=Path, required=True); a.add_argument('--case-id', required=True)
    a = sub.add_parser('screen'); a.add_argument('--run', type=Path, required=True)
    a = sub.add_parser('reconcile'); a.add_argument('--run', type=Path, required=True)
    a = sub.add_parser('stage2-config'); a.add_argument('--benchmark-run', type=Path, required=True)
    a.add_argument('--model', action='append', required=True); a.add_argument('--reason', required=True)
    a.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.command == 'prepare': prepare(args.source, args.output)
    elif args.command == 'plan': print(json.dumps(plan(args.bundle, read(args.config), args.arm), indent=2))
    elif args.command == 'run': run(args.bundle, args.config, args.output, args.arm, args.approve_paid, args.scripted)
    elif args.command == 'smoke-bundle': smoke(args.bundle)
    elif args.command == 'score':
        from scoring import score_run
        score_run(args.run)
    elif args.command == 'review-score':
        from scoring import score_review
        score_review(args.run)
    elif args.command == 'screen':
        from design import screening
        print(json.dumps(screening(args.run), ensure_ascii=False, indent=2))
    elif args.command == 'reconcile':
        from billing import Accounting
        if not os.getenv('OPENROUTER_API_KEY'):
            raise ValueError('OPENROUTER_API_KEY required for read-only accounting reconciliation')
        folder = args.run.resolve()
        baseline = read(folder / 'billing-baseline.json')
        # Preserve every earlier observation before a later billing settlement query.
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        for name in ['billing.json', 'generations.jsonl']:
            if (folder / name).exists():
                shutil.copyfile(folder / name, folder / (stamp + '-' + name))
        Accounting(os.environ['OPENROUTER_API_KEY'], os.getenv('OPENROUTER_MANAGEMENT_KEY')).reconcile(folder, baseline, jsonl(folder / 'calls.jsonl') if (folder / 'calls.jsonl').exists() else [])
        from scoring import score_run
        score_run(folder)
        print('Read-only billing reconciliation complete; no inference')
    elif args.command == 'stage2-config':
        from design import stage2_config
        config = stage2_config(args.benchmark_run, args.model, args.reason)
        if args.output.exists():
            raise ValueError('Stage-two config already exists; preserve earlier selections')
        dump(args.output, config)
        print(f'Stage-two config created: {args.output}; no model calls')
    elif args.command == 'mechanism':
        bundle, _ = verify_bundle(args.bundle); activate(bundle)
        from engine import mechanism
        mechanism(args.output)
    elif args.command == 'inspect':
        bundle, _ = verify_bundle(args.bundle); activate(bundle)
        from actionmail.application.store import decode_email
        from actionmail.content.reader import read_external_sources
        cases = [c for c in jsonl(bundle / 'dataset.jsonl') if c['case_id'] == args.case_id]
        if len(cases) != 1:
            raise ValueError('Case ID not found or duplicated')
        case = cases[0]; email = decode_email(case['email']); outcome = read_external_sources(email)
        print(json.dumps({'case_id': case['case_id'], 'target': email.target_recipient,
              'sender': email.sender, 'to': email.to_recipients, 'cc': email.cc_recipients,
              'received_at': email.received_at.isoformat() if email.received_at else None,
              'original_sources': outcome.email.sources(include_headers=True),
              'inventory': [{'id': s.source_id, 'kind': s.kind, 'name': s.name} for s in email.external_sources],
              'local_read_failures': list(outcome.failures), 'gold': case['gold'],
              'accepted_outcomes': case['accepted_outcomes'],
              'scope': 'Local reviewer inspection, not a model input or an experiment reading decision.'},
              ensure_ascii=False, indent=2))


if __name__ == '__main__':
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    try:
        main()
    except (ValueError, RuntimeError, OSError) as exc:
        print(f'Experiment stopped: {exc}', file=sys.stderr)
        sys.exit(1)
