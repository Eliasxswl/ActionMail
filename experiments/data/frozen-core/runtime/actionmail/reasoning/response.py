import json
from datetime import date, datetime

from actionmail.domain.decision import ActionResult, Evidence


def parse_model_response(content: str) -> ActionResult:
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError("Model response must be a JSON object")
    expected_keys = {"status", "action", "deadline", "evidence", "review_reason"}
    if set(payload) != expected_keys:
        raise ValueError("Model response must contain exactly the required fields")

    status = payload.get("status")
    if status not in {"action", "no_action", "needs_review"}:
        raise ValueError("Invalid status")

    action = payload.get("action")
    deadline = payload.get("deadline")
    review_reason = payload.get("review_reason")
    evidence_payload = payload.get("evidence", [])
    if action is not None and not isinstance(action, str):
        raise ValueError("action must be a string or null")
    if deadline is not None:
        if not isinstance(deadline, str):
            raise ValueError("deadline must be a string or null")
        parsed = datetime.fromisoformat(deadline.replace("Z", "+00:00")) if "T" in deadline else date.fromisoformat(deadline)
        if isinstance(parsed, datetime) and (parsed.tzinfo is None or parsed.utcoffset() is None):
            raise ValueError("deadline datetime must include a timezone")
    if review_reason is not None and not isinstance(review_reason, str):
        raise ValueError("review_reason must be a string or null")
    if status != "action":
        evidence_payload = []
        if status == "needs_review":
            action = None
            deadline = None
    elif isinstance(evidence_payload, dict):
        evidence_payload = [evidence_payload]
    if status != "needs_review":
        review_reason = None
    if not isinstance(evidence_payload, list):
        raise ValueError("evidence must be a list")

    evidence = []
    for item in evidence_payload:
        if not isinstance(item, dict) or not isinstance(item.get("source_id"), str) or not isinstance(item.get("quote"), str):
            raise ValueError("Each evidence item needs source_id and quote strings")
        evidence.append(Evidence(item["source_id"], item["quote"]))

    return ActionResult(status, action, deadline, tuple(evidence), review_reason)
