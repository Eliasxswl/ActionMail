"""Read-only OpenRouter checks and an explicitly approximate batch cost preview."""

import json
import math
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from actionmail.workflow.pipeline import SYSTEM_PROMPT, _user_prompt
from actionmail.workflow.multi_pipeline import MAX_ACTIONS, V2_SYSTEM_PROMPT


OPENROUTER_BASE = "https://openrouter.ai/api/v1"
MAX_OUTPUT_TOKENS = 800  # Keep in sync with the chat request limit.


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
    input_tokens = sum(math.ceil((len(prompt) + len(_user_prompt(case.email)) + 16) / 4) for case in cases)
    additional_calls = 0
    if external_mode != "body-only":
        for case in cases:
            if not case.email.external_sources:
                continue
            additional_calls += 1
            external_chars = sum(
                len(source.snapshot_text) if source.snapshot_text is not None else 20_000
                for source in case.email.external_sources[:2]
            )
            input_tokens += math.ceil((len(prompt) + len(_user_prompt(case.email)) + external_chars + 64) / 4)
    output_per_case, samples = prior_output_average(results_root, model)
    model_calls = len(cases) + additional_calls
    output_tokens = model_calls * output_per_case
    cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000 + model_calls * request_price
    cap_cost = (input_tokens * input_price + model_calls * MAX_OUTPUT_TOKENS * output_price) / 1_000_000 + model_calls * request_price
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "output_per_case": output_per_case,
        "model_calls": model_calls,
        "history_samples": samples,
        "estimated_cost_usd": cost,
        "output_cap_scenario_usd": cap_cost,
    }
