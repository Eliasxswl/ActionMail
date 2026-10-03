import re

from actionmail.domain.decision import ActionResult
from actionmail.domain.email import EmailPackage


_ABBREVIATION = re.compile(r"\b(?:Inc|Ltd|Corp|Co|Dr|Mr|Mrs|Ms|Jr|Sr|St)\.$", re.IGNORECASE)


def align_evidence_quote(quote: str, source: str, *, allow_soft_wrap: bool = False) -> str:
    """Recover a unique source span after whitespace or abbreviation-dot drift."""
    if quote in source:
        return quote

    def canonical(text: str, soft_wrap=False) -> tuple[str, list[int]]:
        characters: list[str] = []
        offsets: list[int] = []
        omitted = {i for match in re.finditer(r'=\r?\n', text) for i in range(match.start(), match.end())} if soft_wrap else set()
        for index, character in enumerate(text):
            if index in omitted:
                continue
            if character == "." and _ABBREVIATION.search(text[:index + 1]):
                continue
            if character.isspace():
                if characters and characters[-1] == " ":
                    continue
                character = " "
            characters.append(character)
            offsets.append(index)
        return "".join(characters), offsets

    normalized_quote, _ = canonical(quote.strip())
    normalized_source, offsets = canonical(source)
    if not normalized_quote:
        return quote
    start = normalized_source.find(normalized_quote)
    if start < 0 and allow_soft_wrap:
        normalized_quote, _ = canonical(quote.strip(), True)
        normalized_source, offsets = canonical(source, True)
        start = normalized_source.find(normalized_quote)
    if start < 0 or normalized_source.find(normalized_quote, start + 1) >= 0:
        return quote
    return source[offsets[start]:offsets[start + len(normalized_quote) - 1] + 1]


def evidence_errors(email: EmailPackage, decision: ActionResult, *, include_headers: bool = False) -> list[str]:
    sources = email.sources(include_headers=include_headers)
    errors = []
    if decision.status == "action":
        if not decision.action or not decision.action.strip():
            errors.append("An action result must include an action")
        if not decision.evidence:
            errors.append("An action result must include evidence")
        if decision.evidence and all(item.source_id.startswith("thread:") for item in decision.evidence):
            errors.append("A prior-thread request needs supporting evidence in the newest message")
    if decision.status == "no_action" and (decision.action is not None or decision.deadline is not None):
        errors.append("A no_action result cannot include an action or deadline")
    if decision.status != "needs_review" and email.unread_sources:
        errors.append("Unread external content prevents a definitive result")
    if decision.status != "needs_review" and not email.body.strip():
        errors.append("An empty newest-message body requires review")
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
