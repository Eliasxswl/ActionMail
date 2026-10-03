import json
from datetime import date, datetime

from actionmail.domain.decision import Evidence, Explanation, MultiActionResult, ProposedAction


def parse_multi_response(content: str, *, require_explanation: bool = False) -> MultiActionResult:
    payload = json.loads(content)
    if isinstance(payload, dict) and set(payload) == {'status', 'actions', 'reason', 'evidence'}:
        payload = {'status': payload['status'], 'actions': payload['actions'],
                   'review_reason': payload['reason'] if payload['status'] == 'needs_review' else None,
                   'explanation': {'text': payload['reason'], 'evidence': payload['evidence']}}
    keys = {"status", "actions", "review_reason"}
    if not isinstance(payload, dict) or set(payload) not in (keys, keys | {'explanation'}):
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
        evidence_items = item["evidence"]
        if isinstance(evidence_items, dict):
            evidence_items = [evidence_items]
        if not isinstance(evidence_items, list) or not evidence_items:
            raise ValueError("Each V2 action needs evidence")
        evidence = []
        for entry in evidence_items:
            if not isinstance(entry, dict) or set(entry) != {"source_id", "quote"} or not all(isinstance(entry[key], str) for key in entry):
                raise ValueError("V2 evidence needs source_id and quote strings")
            evidence.append(Evidence(entry["source_id"], entry["quote"]))
        actions.append(ProposedAction(item["kind"], item["text"], deadline, tuple(evidence)))
    explanation = None
    if 'explanation' in payload:
        item = payload['explanation']
        if not isinstance(item, dict) or set(item) != {'text', 'evidence'} or not isinstance(item['text'], str) or not item['text'].strip() or not isinstance(item['evidence'], list):
            raise ValueError('Explanation requires text and an evidence array')
        quotes = []
        for entry in item['evidence']:
            if not isinstance(entry, dict) or set(entry) != {'source_id', 'quote'} or not all(isinstance(v, str) and v.strip() for v in entry.values()):
                raise ValueError('Explanation evidence requires nonempty source_id and quote strings')
            quotes.append(Evidence(**entry))
        explanation = Explanation(item['text'], tuple(quotes))
        if status != 'needs_review' and not quotes:
            raise ValueError('Definitive explanations require original evidence')
    elif require_explanation:
        raise ValueError('New V2 model responses require an explanation')
    return MultiActionResult(status, tuple(actions), explanation.text if explanation else reason, explanation.evidence if explanation else ())
