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
class Explanation:
    text: str
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class MultiActionResult:
    status: Status
    actions: tuple[ProposedAction, ...]
    reason: str | None
    evidence: tuple[Evidence, ...] = ()

    @property
    def review_reason(self) -> str | None:
        return self.reason if self.status == 'needs_review' else None

    @property
    def explanation(self) -> Explanation | None:
        # Compatibility accessor; serialized new results contain only reason/evidence.
        return Explanation(self.reason, self.evidence) if self.reason else None

    @property
    def action_count(self) -> int:
        return len(self.actions)
