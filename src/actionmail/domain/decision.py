from dataclasses import dataclass
from typing import Literal


Status = Literal["action", "no_action", "needs_review"]
ActionKind = Literal["answer_question", "perform_task", "follow_up"]


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


@dataclass(frozen=True)
class ProposedAction:
    kind: ActionKind
    text: str
    deadline: str | None
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class MultiActionResult:
    status: Status
    actions: tuple[ProposedAction, ...]
    review_reason: str | None

    @property
    def action_count(self) -> int:
        return len(self.actions)
