import re

from actionmail.domain.decision import ActionResult, Evidence
from actionmail.domain.email import EmailPackage


REQUEST_PATTERN = re.compile(
    r"\b(please|can you|could you|would you|do you|will you|shall i|let's|need you|respond|reply|confirm|advise|coordinate)\b",
    re.IGNORECASE,
)


def predict_rules(email: EmailPackage) -> ActionResult:
    if email.unread_sources:
        return ActionResult("needs_review", None, None, (), "External content was not read")
    for source_id in ("body", "subject"):
        text = email.sources()[source_id]
        for line in text.splitlines():
            quote = line.strip()
            if quote and REQUEST_PATTERN.search(quote):
                return ActionResult("action", "Respond to the request in the email.", None, (Evidence(source_id, quote),), None)
    return ActionResult("no_action", None, None, (), None)
