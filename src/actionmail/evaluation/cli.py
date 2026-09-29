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
from actionmail.evaluation.history import print_history
from actionmail.evaluation.metrics import summarize
from actionmail.evaluation.preflight import PreflightError, account_balance, estimate, key_allowance, model_prices
from actionmail.guardrails.evidence import evidence_errors
from actionmail.interfaces.cli import OPENROUTER_API_URL
from actionmail.reasoning.api_client import APIClient, ModelCallError
from actionmail.workflow.pipeline import SYSTEM_PROMPT, process_email


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = PROJECT_ROOT / "evaluation" / "cases.jsonl"
DEFAULT_MAILEX_ROOT = PROJECT_ROOT.parent / "data"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="actionmail-eval", description="Validate or run the frozen 50-case evaluation.")
    parser.add_argument("--validate", action="store_true", help="Validate the frozen cases without making model calls")
    parser.add_argument("--history", action="store_true", help="Summarize saved evaluation runs without a model call")
    parser.add_argument("--preflight", action="store_true", help="Show balance and expected cost, then stop before model calls")
    parser.add_argument("--engine", choices=("rules", "llm"), default="llm")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--mailex-root", type=Path, default=DEFAULT_MAILEX_ROOT)
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
    preview = estimate(cases, PROJECT_ROOT / "results" / "evaluation", args.model, input_price, output_price, request_price)
    print(f"Prices ({source}): ${input_price:.4f}/M input, ${output_price:.4f}/M output, ${request_price:.6f}/request")
    print(f"Approximate tokens: {preview['input_tokens']} input; {preview['output_tokens']} output")
    basis = f"{preview['history_samples']} prior same-model results" if preview["history_samples"] else "160 output tokens/case fallback"
    print(f"Output assumption: {preview['output_per_case']} tokens/case from {basis}")
    print(f"Expected batch cost: about ${preview['estimated_cost_usd']:.6f}")
    print(f"If every answer reaches the 800-token output cap: about ${preview['output_cap_scenario_usd']:.6f} (input still estimated)")
    print("This is a planning estimate; actual tokens, routing, and billed charges may differ.")
    return input_price, output_price, request_price, source


def _run_one(case, engine: str, model: APIClient | None, prices: tuple[float | None, float | None, float]) -> dict:
    reply = None
    error = None
    validation_errors = []
    prediction = None
    try:
        if engine == "rules":
            prediction = predict_rules(case.email)
            validation_errors = evidence_errors(case.email, prediction)
        else:
            run = process_email(case.email, model)
            prediction = run.decision
            reply = run.reply
            validation_errors = list(run.validation_errors)
    except (ModelCallError, OSError, ValueError) as exc:
        error = str(exc)

    usage = None
    cost = None
    if reply is not None:
        usage = {"input_tokens": reply.input_tokens, "output_tokens": reply.output_tokens, "latency_ms": reply.latency_ms}
        if None not in (*prices, reply.input_tokens, reply.output_tokens):
            cost = (reply.input_tokens * prices[0] + reply.output_tokens * prices[1]) / 1_000_000 + prices[2]
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
        "status_correct": prediction.status == case.gold["status"] if prediction else False,
        "safe_external_abstention": case.record["category"] == "external_content" and prediction is not None and prediction.status == "needs_review",
        "validation_errors": validation_errors,
        "error": error,
        "model": reply.model if reply else None,
        "raw_model_response": reply.content if reply else None,
        "usage": usage,
        "estimated_cost_usd": cost,
        "manual_action_correct": None,
        "manual_evidence_supports_action": None,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.history:
            print_history(PROJECT_ROOT / "results" / "evaluation")
            return 0
        cases = load_cases(args.manifest, args.mailex_root)
        if args.validate:
            print(f"Validated {len(cases)} frozen cases: 15 no-action, 15 explicit-action, 10 context, 5 attachment, 5 link.")
            return 0
        if args.limit is not None and args.limit < 1:
            raise ValueError("--limit must be positive")
        if args.case_id and args.limit:
            raise ValueError("Use --case-id or --limit, not both")
        if (args.input_price_per_million is None) != (args.output_price_per_million is None):
            raise ValueError("Provide both token prices or neither")
        if any(value is not None and value < 0 for value in (args.input_price_per_million, args.output_price_per_million)):
            raise ValueError("Token prices cannot be negative")
        if args.case_id:
            wanted = set(args.case_id)
            selected = [case for case in cases if case.case_id in wanted]
            if len(selected) != len(wanted):
                raise ValueError("Unknown --case-id in frozen manifest")
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
            "model": args.model if args.engine == "llm" else "rules-v1",
            "api_url": args.api_url if args.engine == "llm" else None,
            "manifest_sha256": manifest_hash,
            "code_sha256": code_hash.hexdigest(),
            "prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest() if args.engine == "llm" else None,
            "case_ids": [case.case_id for case in selected],
            "input_price_per_million_usd": args.input_price_per_million,
            "output_price_per_million_usd": args.output_price_per_million,
            "price_source": "operator-supplied; verify provider pricing for the run date" if args.input_price_per_million is not None else None,
        }
        meta_path = output / "run.json"
        rows_path = output / "cases.jsonl"
        if args.resume:
            prior = json.loads(meta_path.read_text(encoding="utf-8"))
            for key in ("engine", "model", "api_url", "manifest_sha256", "code_sha256", "prompt_sha256", "case_ids", "input_price_per_million_usd", "output_price_per_million_usd"):
                if prior[key] != metadata[key]:
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
        if not args.resume:
            output.mkdir(parents=True, exist_ok=False)
            _write_json(meta_path, metadata)
            rows_path.touch()
        elif pending:
            _write_json(meta_path, metadata)
        for index, case in enumerate(pending, start=1):
            row = _run_one(case, args.engine, model, prices)
            with rows_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)
            _write_json(output / "summary.json", summarize(rows, len(cases)))
            status = row["prediction"]["status"] if row["prediction"] else "error"
            print(f"[{index}/{len(pending)}] {case.case_id}: {status} (gold: {case.gold['status']})")
        _write_json(output / "summary.json", summarize(rows, len(cases)))
        print(f"Saved {len(rows)} case result(s) in {output}")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
