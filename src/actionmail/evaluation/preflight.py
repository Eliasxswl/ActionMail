"""Read-only OpenRouter checks and an explicitly approximate batch cost preview."""

import json
import math
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from actionmail.workflow.pipeline import SYSTEM_PROMPT, _user_prompt
from actionmail.workflow.multi_pipeline import MAX_ACTIONS, V2_SYSTEM_PROMPT
from actionmail.reasoning.api_client import MAX_OUTPUT_TOKENS


OPENROUTER_BASE = "https://openrouter.ai/api/v1"


class PreflightError(ValueError):
    pass


def _get(path: str, key: str) -> dict:
    request = Request(
        OPENROUTER_BASE + path,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise PreflightError(f"OpenRouter {path} returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise PreflightError(f"OpenRouter {path} could not be read") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise PreflightError(f"OpenRouter {path} returned an unexpected response")
    return payload["data"]


def account_balance(management_key: str) -> float:
    data = _get("/credits", management_key)
    try:
        return float(data["total_credits"]) - float(data["total_usage"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PreflightError("OpenRouter credits response lacks totals") from exc


def key_allowance(api_key: str) -> dict:
    return _get("/key", api_key)


def model_prices(api_key: str, model: str) -> tuple[float, float, float]:
    data = _get("/model/" + quote(model, safe="/"), api_key)
    if data.get("id") != model and data.get("canonical_slug") != model:
        raise PreflightError("OpenRouter returned pricing for a different model")
    pricing = data.get("pricing")
    if not isinstance(pricing, dict):
        raise PreflightError("OpenRouter model response lacks pricing")
    try:
        prompt = float(pricing["prompt"])
        completion = float(pricing["completion"])
        request = float(pricing.get("request") or 0)
    except (KeyError, TypeError, ValueError) as exc:
        raise PreflightError("OpenRouter model prices are unavailable") from exc
    if any(not math.isfinite(value) or value < 0 for value in (prompt, completion, request)):
        raise PreflightError("OpenRouter model prices are invalid")
    return prompt * 1_000_000, completion * 1_000_000, request


def prior_output_average(results_root: Path, model: str) -> tuple[int, int]:
    output = []
    for run_path in results_root.glob("*/run.json"):
        try:
            run = json.loads(run_path.read_text(encoding="utf-8"))
            if run.get("engine") != "llm" or run.get("model") != model:
                continue
            for line in (run_path.parent / "cases.jsonl").read_text(encoding="utf-8").splitlines():
                value = (json.loads(line).get("usage") or {}).get("output_tokens")
                if isinstance(value, int) and value >= 0:
                    output.append(value)
        except (OSError, ValueError, KeyError):
            continue
    return (round(sum(output) / len(output)), len(output)) if output else (160, 0)


def estimate(cases, results_root: Path, model: str, input_price: float, output_price: float, request_price: float = 0, external_mode: str = "body-only", schema: str = "v1") -> dict:
    # Character count is only a rough proxy for provider-tokenizer input tokens.
    prompt = SYSTEM_PROMPT if schema == "v1" else V2_SYSTEM_PROMPT.format(max_actions=MAX_ACTIONS)
    input_tokens = 0
    model_calls = 0
    repair_budgets = []
    if schema == 'v2':
        from actionmail.content.reader import read_external_sources, MAX_TEXT_CHARS
        from actionmail.workflow.coverage import WorkflowLimits, PLAN_PROMPT, segments
        for case in cases:
            calls_before = model_calls
            limits = WorkflowLimits(**case.record.get('workflow_limits', {}))
            email = case.email
            body_sources = {'body': email.body, **{s.source_id: s.text for s in email.thread}}
            if external_mode != 'body-only' and email.external_sources:
                try:
                    plan_windows = segments(body_sources, limits)
                except ValueError:
                    continue  # Actual workflow stops before any call.
                inventory_chars = sum(len(s.name) + len(s.source_id) + 128 for s in email.external_sources)
                model_calls += len(plan_windows)
                input_tokens += sum(math.ceil((len(PLAN_PROMPT) + len(w.text) + inventory_chars + 2048) / 4) for w in plan_windows)
                outcome = read_external_sources(email)
                sources = {**email.sources(include_headers=True), **{s.source_id: s.text for s in outcome.email.read_sources}}
                for source in email.external_sources:
                    if source.source_id not in sources and source.kind == 'link' and source.snapshot_text is None and external_mode == 'allowed-live':
                        sources[source.source_id] = ' ' * MAX_TEXT_CHARS  # Unavailable live/file content upper scenario.
            else:
                sources = email.sources(include_headers=True)
            try:
                windows = segments(sources, limits)
            except ValueError:
                # Unknown live sizes: budgeted worst case, not an assumed two-call path.
                windows = None
            total = sum(len(t) for t in sources.values())
            if total <= limits.segment_chars:
                model_calls += 1
                input_tokens += math.ceil((len(prompt) + total + 2048) / 4)
            else:
                count = len(windows) if windows is not None else limits.max_segments
                model_calls += count + 1
                # Candidate/newest context can grow up to the merge budget on each segment.
                input_tokens += count * math.ceil((len(prompt) + limits.segment_chars + limits.max_merge_chars + 2048) / 4)
                input_tokens += math.ceil((len(prompt) + limits.max_merge_chars) / 4)
            if model_calls > calls_before:
                repair_budgets.append(limits.max_merge_chars)
        # One possible validation repair per email, not one per segment/stage.
        model_calls += len(repair_budgets)
        input_tokens += sum(math.ceil((len(prompt) + budget) / 4) for budget in repair_budgets)
    else:
        input_tokens = sum(math.ceil((len(prompt) + len(_user_prompt(case.email)) + 16) / 4) for case in cases)
        model_calls = len(cases)
        if external_mode != 'body-only':
            for case in cases:
                if case.email.external_sources:
                    model_calls += 1
                    external_chars = sum(len(s.snapshot_text) if s.snapshot_text is not None else 200_000 for s in case.email.external_sources)
                    input_tokens += math.ceil((len(prompt) + len(_user_prompt(case.email)) + external_chars + 64) / 4)
    output_per_case, samples = prior_output_average(results_root, model)
    output_tokens = model_calls * output_per_case
    cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000 + model_calls * request_price
    cap_cost = (input_tokens * input_price + model_calls * MAX_OUTPUT_TOKENS * output_price) / 1_000_000 + model_calls * request_price
    return {
        "estimate_scope": "Conservative all-source planning/segment/merge scenario, including at most one validation repair per v2 email; source selection and failures may reduce calls",
        "max_validation_repairs": len(repair_budgets),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "output_per_case": output_per_case,
        "model_calls": model_calls,
        "history_samples": samples,
        "estimated_cost_usd": cost,
        "output_cap_scenario_usd": cap_cost,
    }
