from actionmail.domain.decision import ActionResult
from actionmail.domain.email import EmailPackage


def evidence_errors(email: EmailPackage, decision: ActionResult) -> list[str]:
    sources = email.sources()
    errors = []
    if decision.status == "action":
        if not decision.action or not decision.action.strip():
            errors.append("An action result must include an action")
        if not decision.evidence:
            errors.append("An action result must include evidence")
    if decision.status == "no_action" and (decision.action is not None or decision.deadline is not None):
        errors.append("A no_action result cannot include an action or deadline")
    if decision.status != "needs_review" and email.unread_sources:
        errors.append("Unread external content prevents a definitive result")
    if decision.status == "no_action" and not any(text.strip() for text in sources.values()):
        errors.append("An empty email cannot support a definitive no_action result")
    if decision.status == "needs_review" and not (decision.review_reason or "").strip():
        errors.append("A needs_review result must include a reason")
    if decision.status == "needs_review" and (decision.action is not None or decision.deadline is not None):
        errors.append("A needs_review result cannot include a final action or deadline")

    for item in decision.evidence:
        source = sources.get(item.source_id)
        if source is None:
            errors.append(f"Unknown evidence source: {item.source_id}")
        elif not item.quote.strip() or item.quote not in source:
            errors.append(f"Evidence quote is absent from source: {item.source_id}")
    return errors
