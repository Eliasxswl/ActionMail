from dataclasses import dataclass
from datetime import datetime
import re


_ADDRESS_PATTERN = re.compile(r"(?<![\w@])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w@])")


def addresses_in_header(header: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_ADDRESS_PATTERN.findall(header)))


@dataclass(frozen=True)
class SourceText:
    source_id: str
    text: str
    sender: str = ""
    recipients: str = ""
    cc: str = ""
    subject: str = ""


@dataclass(frozen=True)
class ExternalSource:
    source_id: str
    kind: str
    name: str
    snapshot_text: str | None = None
    content: bytes | None = None
    media_type: str | None = None
    charset: str | None = None


@dataclass(frozen=True)
class EmailPackage:
    case_id: str
    target_recipient: str
    received_at: datetime | None
    sender: str
    recipients: tuple[str, ...]
    subject: str
    body: str
    thread: tuple[SourceText, ...] = ()
    unread_sources: tuple[str, ...] = ()
    to_recipients: tuple[str, ...] = ()
    cc_recipients: tuple[str, ...] = ()
    external_sources: tuple[ExternalSource, ...] = ()
    read_sources: tuple[SourceText, ...] = ()
    legacy_soft_wraps: bool = False

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id is required")
        if not self.target_recipient.strip():
            raise ValueError("target_recipient is required")
        if self.received_at is not None and (self.received_at.tzinfo is None or self.received_at.utcoffset() is None):
            raise ValueError("received_at must include a timezone")

    def sources(self) -> dict[str, str]:
        items = {"subject": self.subject, "body": self.body}
        for source in self.thread:
            if source.source_id in items:
                raise ValueError(f"Duplicate source_id: {source.source_id}")
            items[source.source_id] = source.text
        for source in self.read_sources:
            if source.source_id in items:
                raise ValueError(f"Duplicate source_id: {source.source_id}")
            items[source.source_id] = source.text
        return items
