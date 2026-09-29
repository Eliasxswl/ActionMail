import hashlib
import http.client
import io
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from pypdf.errors import PyPdfError

from actionmail.domain.email import EmailPackage, ExternalSource, SourceText


MAX_SOURCES = 2
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_TEXT_CHARS = 20_000


@dataclass(frozen=True)
class ReadRecord:
    source_id: str
    name: str
    method: str
    sha256: str
    characters: int


@dataclass(frozen=True)
class ReadOutcome:
    email: EmailPackage
    records: tuple[ReadRecord, ...]
    failures: tuple[str, ...]


class _VisibleHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.ignored:
            self.ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.parts.append(data)


def _text_from_bytes(source: ExternalSource) -> str:
    content = source.content
    if content is None:
        raise ValueError("No local attachment content is available")
    if len(content) > MAX_SOURCE_BYTES:
        raise ValueError("Source exceeds the 2 MiB limit")
    media_type = (source.media_type or "").lower()
    if media_type in {"text/plain", "text/csv", "text/html"}:
        decoded = content.decode(source.charset or "utf-8-sig")
        if media_type == "text/html":
            parser = _VisibleHtml()
            parser.feed(decoded)
            return " ".join(parser.parts).strip()
        return decoded
    if media_type == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDF requires manual review")
        if len(reader.pages) > 20:
            raise ValueError("PDF exceeds the 20-page limit")
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    raise ValueError(f"Unsupported attachment type: {media_type or 'unknown'}")


def read_external_sources(email: EmailPackage, *, fetch_live=None) -> ReadOutcome:
    """Read only inventoried sources; live links require an explicit fetcher."""
    if len(email.external_sources) > MAX_SOURCES:
        return ReadOutcome(email, (), ("More than two external sources require manual selection",))
    read = []
    records = []
    failures = []
    pending = []
    for source in email.external_sources:
        try:
            if source.snapshot_text is not None:
                content = source.snapshot_text.encode("utf-8")
                method = "frozen_snapshot"
                text = source.snapshot_text
            elif source.kind == "attachment":
                content = source.content or b""
                method = "local_attachment"
                text = _text_from_bytes(source)
            elif source.kind == "link" and fetch_live is not None:
                content, media_type, charset = fetch_live(source.name)
                method = "allowlisted_https"
                text = _text_from_bytes(replace(source, content=content, media_type=media_type, charset=charset))
            else:
                raise ValueError("No approved snapshot or live reader is available")
            if len(content) > MAX_SOURCE_BYTES:
                raise ValueError("Source exceeds the 2 MiB limit")
            if not text.strip():
                raise ValueError("Source contains no extractable text")
            if len(text) > MAX_TEXT_CHARS:
                raise ValueError("Extracted text exceeds the 20,000-character limit")
            read.append(SourceText(source.source_id, text))
            records.append(ReadRecord(source.source_id, source.name, method, hashlib.sha256(content).hexdigest(), len(text)))
        except (OSError, UnicodeError, ValueError, LookupError, PyPdfError, http.client.HTTPException) as exc:
            pending.append(source.name)
            failures.append(f"{source.source_id}: {exc}")
    return ReadOutcome(
        replace(email, read_sources=tuple(read), unread_sources=tuple(pending)),
        tuple(records), tuple(failures),
    )
