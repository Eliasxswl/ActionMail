from dataclasses import dataclass
from typing import Literal


Status = Literal["action", "no_action", "needs_review"]


@dataclass(frozen=True)
class Evidence:
    source_id: str
    quote: str


@dataclass(frozen=True)
class ActionResult:
    status: Status
    action: str | None
    deadline: str | None
    evidence: tuple[Evidence, ...]
    review_reason: str | None
