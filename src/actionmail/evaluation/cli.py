import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from actionmail.evaluation.baseline import predict_rules
from actionmail.evaluation.cases import load_cases
from actionmail.evaluation.challenge import load_challenge, prepare_challenge, challenge_checks, approve_challenge_gold
from actionmail.workflow.coverage import WorkflowLimits, PLAN_PROMPT
from actionmail.evaluation.history import print_history
from actionmail.evaluation.metrics import summarize, summarize_v2
from actionmail.evaluation.multi_draft import load_multi_drafts
from actionmail.evaluation.preflight import PreflightError, account_balance, estimate, key_allowance, model_prices
from actionmail.content.links import fetch_allowlisted_https
from actionmail.guardrails.evidence import evidence_errors
from actionmail.interfaces.cli import OPENROUTER_API_URL
from actionmail.reasoning.api_client import APIClient, ModelCallError
from actionmail.workflow.pipeline import SYSTEM_PROMPT, process_email, process_email_with_external
from actionmail.workflow.multi_pipeline import MAX_ACTIONS, V2_SYSTEM_PROMPT, process_email_multi, process_email_multi_with_external


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = PROJECT_ROOT / "evaluation" / "cases.jsonl"
DEFAULT_MAILEX_ROOT = PROJECT_ROOT.parent / "data"
DEFAULT_MULTI_DRAFT = PROJECT_ROOT / "evaluation" / "multi_action_draft.jsonl"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="actionmail-eval", description="Validate or run the frozen 50-case evaluation.")
    parser.add_argument("--validate", action="store_true", help="Validate the frozen cases without making model calls")
    parser.add_argument('--benchmark', choices=('frozen', 'supplement-v2', 'challenge-v2.1'), default='frozen')
    parser.add_argument('--prepare-challenge', action='store_true', help='Create a reference-only review run without model calls')
    parser.add_argument('--approve-challenge-gold', type=Path, help='Reference-preview directory with all owner gold judgments saved correct; no model call')
    parser.add_argument('--approved-manifest', type=Path, help='New approved challenge manifest path')
    parser.add_argument("--history", action="store_true", help="Summarize saved evaluation runs without a model call")
    parser.add_argument("--preflight", action="store_true", help="Show balance and expected cost, then stop before model calls")
    parser.add_argument("--engine", choices=("rules", "llm"), default="llm")
    parser.add_argument("--schema", choices=("v1", "v2"), default="v1", help="Use the v2 three-action result contract when selected")
    parser.add_argument("--external-mode", choices=("body-only", "snapshots", "allowed-live"), default="body-only")
    parser.add_argument("--allow-domain", action="append", default=[], help="Explicitly allow a domain for live HTTPS reading")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--mailex-root", type=Path, default=DEFAULT_MAILEX_ROOT)
    parser.add_argument("--multi-draft", type=Path, default=DEFAULT_MULTI_DRAFT, help="Pending-owner multi-action reference proposals")
    parser.add_argument("--case-group", choices=("external", "multi-draft"), help="Select the 10 frozen external cases or A16/C13")
    parser.add_argument("--prepare-multi", action="store_true", help="Validate and show draft multi-action references without API calls")
    parser.add_argument("--model", default=os.getenv("ACTIONMAIL_MODEL"))
    parser.add_argument("--api-url", default=os.getenv("ACTIONMAIL_API_URL", OPENROUTER_API_URL))
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--management-key-env", default="OPENROUTER_MANAGEMENT_KEY", help="Optional key for OpenRouter account credit balance")
    parser.add_argument("--input-price-per-million", type=float)
    parser.add_argument("--output-price-per-million", type=float)
    parser.add_argument("--limit", type=int, help="Run the first N cases as a smoke test")
    parser.add_argument("--case-id", action="append", help="Run only a named case; repeat to select several cases")
    parser.add_argument("--output-dir", type=Path, help="Result directory; defaults to a unique directory under results/evaluation")
    parser.add_argument("--resume", action="store_true", help="Continue a matching interrupted run")
    parser.add_argument("--yes", action="store_true", help="Confirm the batch model calls without an interactive prompt")
    return parser


def _write_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _show_preflight(args, cases, api_key: str) -> tuple[float, float, float, str]:
    print(f"Preflight: {len(cases)} pending case(s); model {args.model}")
    provider_prices = None
    request_price = 0.0
    if args.api_url == OPENROUTER_API_URL:
        try:
            key = key_allowance(api_key)
            print(f"OpenRouter key usage: ${float(key['usage']):.4f}" if key.get("usage") is not None else "OpenRouter key usage: unavailable")
            remaining = key.get("limit_remaining")
            print(f"Key spending limit remaining: ${float(remaining):.4f}" if remaining is not None else "Key spending limit remaining: no limit reported")
        except (PreflightError, TypeError, ValueError) as exc:
            print(f"OpenRouter key allowance: unavailable ({exc})")
        management_key = os.getenv(args.management_key_env)
        if management_key:
            try:
                print(f"Account credit balance: ${account_balance(management_key):.4f}")
            except PreflightError as exc:
                print(f"Account credit balance: unavailable ({exc})")
        else:
            print(f"Account credit balance: unavailable; set {args.management_key_env} locally to query it")
        try:
            provider_prices = model_prices(api_key, args.model)
            request_price = provider_prices[2]
        except PreflightError as exc:
            print(f"Live model pricing: unavailable ({exc})")
    else:
        print("Balance and live pricing: unavailable for a custom API URL")

    if args.input_price_per_million is not None:
        input_price, output_price = args.input_price_per_million, args.output_price_per_million
        source = "operator-supplied"
    elif provider_prices is not None:
        input_price, output_price = provider_prices[:2]
        source = "OpenRouter model catalog at preflight"
    else:
        raise PreflightError("Cannot estimate cost; provide both token prices or restore OpenRouter pricing access")
    preview = estimate(cases, PROJECT_ROOT / "results" / "evaluation", args.model, input_price, output_price, request_price, args.external_mode, args.schema)
    print(f"Prices ({source}): ${input_price:.4f}/M input, ${output_price:.4f}/M output, ${request_price:.6f}/request")
    print(f"Approximate tokens: {preview['input_tokens']} input; {preview['output_tokens']} output")
    print(f"Expected model calls: up to {preview['model_calls']}")
    basis = f"{preview['history_samples']} prior same-model results" if preview["history_samples"] else "160 output tokens/case fallback"
    print(f"Output assumption: {preview['output_per_case']} tokens/case from {basis}")
    print(f"Expected batch cost: about ${preview['estimated_cost_usd']:.6f}")
    print(f"If every answer reaches the 800-token output cap: about ${preview['output_cap_scenario_usd']:.6f} (input still estimated)")
    print("This is a planning estimate; actual tokens, routing, and billed charges may differ.")
    return input_price, output_price, request_price, source


def _run_one(case, engine: str, model: APIClient | None, prices: tuple[float | None, float | None, float], external_mode: str = "body-only", allow_domains: tuple[str, ...] = (), schema: str = "v1", multi_draft: dict | None = None) -> dict:
    reply = None
    error = None
    validation_errors = []
    prediction = None
    replies = ()
    read_records = ()
    trace = {}
    try:
        if engine == "rules":
            prediction = predict_rules(case.email)
            validation_errors = evidence_errors(case.email, prediction)
        else:
            fetch_live = (lambda url: fetch_allowlisted_https(url, allow_domains)) if external_mode == "allowed-live" else None
            if schema == "v2":
                limits = WorkflowLimits(**case.record.get('workflow_limits', {}))
                run = process_email_multi(case.email, model, limits=limits) if external_mode == "body-only" else process_email_multi_with_external(case.email, model, fetch_live=fetch_live, limits=limits)
            else:
                run = process_email(case.email, model) if external_mode == "body-only" else process_email_with_external(case.email, model, fetch_live=fetch_live)
            prediction = run.decision
            replies = run.replies if schema == "v2" else run.replies or (run.reply,)
            reply = replies[-1] if replies else None
            read_records = run.read_records
            validation_errors = list(run.validation_errors)
            if schema == 'v2':
                error = run.model_error
                trace = {key: [asdict(item) if hasattr(item, '__dataclass_fields__') else item for item in getattr(run, key)]
                         for key in ('source_plan', 'coverage', 'read_failures', 'evidence_locations')}
                trace.update({'failed_model_calls': run.failed_model_calls, 'model_calls_succeeded': len(replies)})
                if case.record.get('challenge_version'):
                    trace.update(challenge_checks(case, run))
    except (ModelCallError, OSError, ValueError) as exc:
        error = str(exc)

    usage = None
    cost = None
    if reply is not None:
        usage = {
            "input_tokens": sum(item.input_tokens or 0 for item in replies),
            "output_tokens": sum(item.output_tokens or 0 for item in replies),
            "latency_ms": sum(item.latency_ms or 0 for item in replies),
        }
        if not error and None not in prices and all(item.input_tokens is not None and item.output_tokens is not None for item in replies):
            cost = (usage["input_tokens"] * prices[0] + usage["output_tokens"] * prices[1]) / 1_000_000 + len(replies) * prices[2]
    established_v2_reference = schema == "v2" and case.record["category"] == "external_content" and multi_draft is None
    status_correct = (
        prediction.status == case.gold["status"] if prediction else False
    ) if schema == "v1" or established_v2_reference else None
    expected_count = 1 if case.gold["status"] == "action" else 0
    action_count_match = (
        prediction is not None and prediction.action_count == expected_count
    ) if established_v2_reference else None
    return {
        "case_id": case.case_id,
        "category": case.record["category"],
        "external_kind": case.record.get("external_kind"),
        "origin": case.record["source"]["kind"],
        "source_file": case.record["source"].get("file"),
        "source_sha256": case.source_hash,
        "target_recipient": case.email.target_recipient,
        "gold": case.gold,
        "prediction": asdict(prediction) if prediction else None,
        "status_correct": status_correct,
        "action_count_match": action_count_match,
        "multi_action_draft": multi_draft,
        "safe_external_abstention": case.record["category"] == "external_content" and prediction is not None and prediction.status == "needs_review" and not read_records,
        "validation_errors": validation_errors,
        "error": error,
        "model": reply.model if reply else None,
        "model_calls": len(replies) + trace.get('failed_model_calls', 0),
        "read_sources": [asdict(item) for item in read_records],
        "raw_model_response": reply.content if reply else None,
        "usage": usage,
        "estimated_cost_usd": cost,
        "manual_action_correct": None,
        "manual_evidence_supports_action": None,
        "raw_model_responses": [item.content for item in replies],
        **trace,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.history:
            print_history(PROJECT_ROOT / "results" / "evaluation")
            return 0
        challenge = args.benchmark in {'challenge-v2.1', 'supplement-v2'}
        if challenge and args.manifest == DEFAULT_MANIFEST:
            if args.benchmark == 'supplement-v2':
                suite = json.loads((PROJECT_ROOT / 'evaluation/active_suite.json').read_text(encoding='utf-8'))
                component = next(c for c in suite['components'] if c['benchmark'] == args.benchmark)
                args.manifest = PROJECT_ROOT / 'evaluation' / component['manifest']
                if hashlib.sha256(args.manifest.read_bytes()).hexdigest() != component['sha256']:
                    raise ValueError('Active supplementary manifest hash mismatch')
            else:
                args.manifest = PROJECT_ROOT / 'evaluation/archive/challenge_v2_1_revision2.jsonl'
        if challenge:
            if args.engine != 'llm' or args.case_group or args.prepare_multi:
                raise ValueError('Challenge uses the v2 LLM workflow; frozen groups/drafts do not apply')
            args.schema = 'v2'
            if args.external_mode == 'allowed-live':
                raise ValueError('Challenge v2.1 gold is defined for snapshots mode; live transport is verified separately')
            args.external_mode = 'snapshots'
        cases = load_challenge(args.manifest, args.mailex_root, benchmark=args.benchmark) if challenge else load_cases(args.manifest, args.mailex_root)
        if args.approve_challenge_gold:
            if not challenge or not args.approved_manifest:
                raise ValueError('--approve-challenge-gold requires a supplementary/challenge benchmark and --approved-manifest')
            destination = approve_challenge_gold(args.manifest, args.approve_challenge_gold, args.approved_manifest)
            print(f'Created approved challenge reference: {destination}')
            return 0
        if args.approved_manifest:
            raise ValueError('--approved-manifest requires --approve-challenge-gold')
        if args.prepare_challenge:
            if not challenge:
                raise ValueError('--prepare-challenge requires a supplementary/challenge benchmark')
            output = args.output_dir or PROJECT_ROOT / 'results' / 'evaluation' / ('challenge-gold-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
            prepare_challenge(cases, args.manifest, output, benchmark=args.benchmark)
            print(f'Prepared {len(cases)} reference-only cases for owner review: {output}')
            return 0
        multi_drafts = load_multi_drafts(args.multi_draft, cases) if not challenge and (args.schema == "v2" or args.prepare_multi or args.case_group == "multi-draft") and args.multi_draft.exists() else {}
        if args.prepare_multi:
            if not multi_drafts:
                raise ValueError(f"Multi-action draft not found: {args.multi_draft}")
            for case in cases:
                draft = multi_drafts.get(case.case_id)
                if draft is None:
                    continue
                print(f"{case.case_id}: {draft['proposed_status']} ({draft['review_state']}; {len(draft['candidate_actions'])} candidate tasks)")
                print(f"  Recipient: {case.email.target_recipient}")
                for index, action in enumerate(draft["candidate_actions"], start=1):
                    print(f"  {index}. {action['text']} [{action['evidence'][0]['source_id']}: {action['evidence'][0]['quote']}]")
                if draft["review_reason"]:
                    print(f"  Review reason: {draft['review_reason']}")
            print("These references are drafts awaiting owner review; no correctness score is assigned.")
            return 0
        if args.external_mode == "allowed-live" and not args.allow_domain:
            raise ValueError("--external-mode allowed-live requires --allow-domain")
        if args.allow_domain and args.external_mode != "allowed-live":
            raise ValueError("--allow-domain requires --external-mode allowed-live")
        if args.engine == "rules" and args.external_mode != "body-only":
            raise ValueError("The rule baseline supports body-only mode")
        if args.engine == "rules" and args.schema != "v1":
            raise ValueError("The rule baseline supports only the v1 schema")
        if args.validate:
            approved_count = sum(c.record.get('review_state') == 'approved' for c in cases)
            print(f'Validated {len(cases)} {args.benchmark} cases; {approved_count} approved references, {len(cases) - approved_count} pending.' if challenge else f"Validated {len(cases)} frozen cases: 15 no-action, 15 explicit-action, 10 context, 5 attachment, 5 link.")
            return 0
        if args.limit is not None and args.limit < 1:
            raise ValueError("--limit must be positive")
        if sum((bool(args.case_id), bool(args.limit), bool(args.case_group))) > 1:
            raise ValueError("Use only one of --case-id, --limit, or --case-group")
        if (args.input_price_per_million is None) != (args.output_price_per_million is None):
            raise ValueError("Provide both token prices or neither")
        if any(value is not None and value < 0 for value in (args.input_price_per_million, args.output_price_per_million)):
            raise ValueError("Token prices cannot be negative")
        if args.case_id:
            wanted = set(args.case_id)
            selected = [case for case in cases if case.case_id in wanted]
            if len(selected) != len(wanted):
                raise ValueError("Unknown --case-id in frozen manifest")
        elif args.case_group == "external":
            selected = [case for case in cases if case.record["category"] == "external_content"]
        elif args.case_group == "multi-draft":
            if not multi_drafts:
                raise ValueError("Multi-action draft is unavailable")
            selected = [case for case in cases if case.case_id in multi_drafts]
            if args.schema != "v2":
                raise ValueError("--case-group multi-draft requires --schema v2")
        else:
            selected = cases[:args.limit] if args.limit else cases
        model = None
        if args.engine == "llm":
            key = os.getenv(args.api_key_env)
            if not args.model:
                raise ValueError("Set ACTIONMAIL_MODEL locally or pass --model before the LLM run")
            if not key:
                raise ValueError(f"Set {args.api_key_env} locally before the LLM run")
            model = APIClient(args.api_url, key, args.model)
        elif args.preflight:
            raise ValueError("--preflight requires --engine llm")
        if args.preflight:
            _show_preflight(args, selected, key)
            return 0

        manifest_hash = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
        source_files = sorted((PROJECT_ROOT / "src" / "actionmail").rglob("*.py"))
        code_hash = hashlib.sha256()
        for source_file in source_files:
            code_hash.update(str(source_file.relative_to(PROJECT_ROOT)).encode("utf-8"))
            code_hash.update(source_file.read_bytes())
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
        output = args.output_dir or PROJECT_ROOT / "results" / "evaluation" / run_id
        metadata = {
            "run_id": run_id,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "engine": args.engine,
            "schema": args.schema,
            "benchmark": args.benchmark,
            "case_group": args.case_group,
            "multi_draft_sha256": hashlib.sha256(args.multi_draft.read_bytes()).hexdigest() if args.schema == "v2" and multi_drafts else None,
            "external_mode": args.external_mode,
            "allowed_domains": args.allow_domain,
            "model": args.model if args.engine == "llm" else "rules-v1",
            "api_url": args.api_url if args.engine == "llm" else None,
            "manifest_sha256": manifest_hash,
            "code_sha256": code_hash.hexdigest(),
            "prompt_sha256": hashlib.sha256((SYSTEM_PROMPT if args.schema == "v1" else V2_SYSTEM_PROMPT.format(max_actions=MAX_ACTIONS) + PLAN_PROMPT).encode("utf-8")).hexdigest() if args.engine == "llm" else None,
            "case_ids": [case.case_id for case in selected],
            "input_price_per_million_usd": args.input_price_per_million,
            "output_price_per_million_usd": args.output_price_per_million,
            "price_source": "operator-supplied; verify provider pricing for the run date" if args.input_price_per_million is not None else None,
        }
        meta_path = output / "run.json"
        rows_path = output / "cases.jsonl"
        if args.resume:
            prior = json.loads(meta_path.read_text(encoding="utf-8"))
            for key in ("engine", "schema", "case_group", "multi_draft_sha256", "external_mode", "allowed_domains", "model", "api_url", "manifest_sha256", "code_sha256", "prompt_sha256", "case_ids", "input_price_per_million_usd", "output_price_per_million_usd"):
                if prior.get(key, "body-only" if key == "external_mode" else [] if key == "allowed_domains" else None) != metadata[key]:
                    raise ValueError(f"Cannot resume: {key} changed")
            metadata = prior
            rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            rows = []
        seen = {row["case_id"] for row in rows}
        if len(seen) != len(rows):
            raise ValueError("Duplicate case results in output")
        pending = [case for case in selected if case.case_id not in seen]
        prices = (args.input_price_per_million, args.output_price_per_million, 0.0)
        if args.engine == "llm" and pending:
            input_price, output_price, request_price, source = _show_preflight(args, pending, key)
            prices = (input_price, output_price, request_price)
            metadata.update({"effective_input_price_per_million_usd": input_price, "effective_output_price_per_million_usd": output_price, "request_price_usd": request_price, "effective_price_source": source})
        if args.engine == "llm" and pending and not args.yes:
            answer = input(f"Send {len(pending)} case(s) to the configured model API? [y/N] ").strip().lower()
            if answer != "y":
                print("Cancelled before model calls.")
                return 0
        if args.external_mode == "allowed-live" and any(
            source.kind == "link" and source.snapshot_text is None
            for case in pending for source in case.email.external_sources
        ) and not args.yes:
            answer = input("Fetch live links from the explicitly allowed domain(s)? [y/N] ").strip().lower()
            if answer != "y":
                print("Cancelled before live link retrieval.")
                return 0
        if not args.resume:
            output.mkdir(parents=True, exist_ok=False)
            _write_json(meta_path, metadata)
            rows_path.touch()
        elif pending:
            _write_json(meta_path, metadata)
        for index, case in enumerate(pending, start=1):
            row = _run_one(case, args.engine, model, prices, args.external_mode, tuple(args.allow_domain), args.schema, multi_drafts.get(case.case_id) if args.schema == "v2" else None)
            with rows_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)
            _write_json(output / "summary.json", summarize(rows, len(selected) if args.case_group else len(cases)) if args.schema == "v1" else summarize_v2(rows, len(selected)))
            status = row["prediction"]["status"] if row["prediction"] else "error"
            print(f"[{index}/{len(pending)}] {case.case_id}: {status} (gold: {case.gold['status']})")
        _write_json(output / "summary.json", summarize(rows, len(selected) if args.case_group else len(cases)) if args.schema == "v1" else summarize_v2(rows, len(selected)))
        print(f"Saved {len(rows)} case result(s) in {output}")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
