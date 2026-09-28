from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SourceText:
    source_id: str
    text: str


@dataclass(frozen=True)
class EmailPackage:
    case_id: str
    target_recipient: str
    received_at: datetime
    sender: str
    recipients: tuple[str, ...]
    subject: str
    body: str
    thread: tuple[SourceText, ...] = ()
    unread_sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id is required")
        if not self.target_recipient.strip():
            raise ValueError("target_recipient is required")
        if self.received_at.tzinfo is None or self.received_at.utcoffset() is None:
            raise ValueError("received_at must include a timezone")

    def sources(self) -> dict[str, str]:
        items = {"subject": self.subject, "body": self.body}
        for source in self.thread:
            if source.source_id in items:
                raise ValueError(f"Duplicate source_id: {source.source_id}")
            items[source.source_id] = source.text
        return items
