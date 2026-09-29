import json
from datetime import date, datetime

from actionmail.domain.decision import Evidence, MultiActionResult, ProposedAction


def parse_multi_response(content: str) -> MultiActionResult:
    payload = json.loads(content)
    if not isinstance(payload, dict) or set(payload) != {"status", "actions", "review_reason"}:
        raise ValueError("V2 response needs exactly status, actions, and review_reason")
    status = payload["status"]
    if status not in {"action", "no_action", "needs_review"}:
        raise ValueError("Invalid V2 status")
    items = payload["actions"]
    if not isinstance(items, list):
        raise ValueError("V2 actions must be a list")
    if (status == "action") != bool(items):
        raise ValueError("V2 action status and actions list disagree")
    reason = payload["review_reason"]
    if status == "needs_review":
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("V2 needs_review requires a reason")
    elif reason is not None:
        raise ValueError("Definitive V2 results cannot have a review reason")
    actions = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"kind", "text", "deadline", "evidence"}:
            raise ValueError("Each V2 action needs kind, text, deadline, and evidence")
        if item["kind"] not in {"answer_question", "perform_task", "follow_up"}:
            raise ValueError("Invalid V2 action kind")
        if not isinstance(item["text"], str) or not item["text"].strip():
            raise ValueError("V2 action text is required")
        deadline = item["deadline"]
        if deadline is not None:
            if not isinstance(deadline, str):
                raise ValueError("V2 deadline must be a string or null")
            parsed = datetime.fromisoformat(deadline.replace("Z", "+00:00")) if "T" in deadline else date.fromisoformat(deadline)
            if isinstance(parsed, datetime) and (parsed.tzinfo is None or parsed.utcoffset() is None):
                raise ValueError("V2 deadline datetime needs a timezone")
        if not isinstance(item["evidence"], list) or not item["evidence"]:
            raise ValueError("Each V2 action needs evidence")
        evidence = []
        for entry in item["evidence"]:
            if not isinstance(entry, dict) or set(entry) != {"source_id", "quote"} or not all(isinstance(entry[key], str) for key in entry):
                raise ValueError("V2 evidence needs source_id and quote strings")
            evidence.append(Evidence(entry["source_id"], entry["quote"]))
        actions.append(ProposedAction(item["kind"], item["text"], deadline, tuple(evidence)))
    return MultiActionResult(status, tuple(actions), reason)
