import base64
import hashlib
import http.client
import io
import re
from dataclasses import dataclass, replace
from html.parser import HTMLParser

from actionmail.domain.email import EmailPackage, ExternalSource, SourceText
from actionmail.content.office import office_parts

MAX_SOURCES = 12
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_TEXT_CHARS = 200_000

@dataclass(frozen=True)
class ReadLimits:
    max_sources: int = MAX_SOURCES
    max_bytes: int = MAX_SOURCE_BYTES
    max_text_chars: int = MAX_TEXT_CHARS
    max_total_chars: int = 300_000

    def __post_init__(self):
        if min(self.max_sources, self.max_bytes, self.max_text_chars, self.max_total_chars) < 1:
            raise ValueError('Reading budgets must be positive')

@dataclass(frozen=True)
class Location:
    label: str
    start: int
    end: int

@dataclass(frozen=True)
class ReadRecord:
    source_id: str
    name: str
    method: str
    sha256: str
    characters: int
    bytes: int = 0
    media_type: str | None = None
    final_url: str | None = None
    retrieved_at: str | None = None
    locations: tuple[Location, ...] = ()
    extracted_text: str = ''
    replay_base64: str | None = None
    extraction_method: str = ''
    charset: str | None = None

@dataclass(frozen=True)
class ReadOutcome:
    email: EmailPackage
    records: tuple[ReadRecord, ...]
    failures: tuple[str, ...]

class _VisibleHtml(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.ignored = 0
        self.login_form = False
    def handle_starttag(self, tag, attrs):
        if tag == 'input' and dict(attrs).get('type', '').lower() == 'password':
            self.login_form = True
        if tag in {'script', 'style'}:
            self.ignored += 1
        if tag in {'p', 'div', 'br', 'li', 'tr'} and not self.ignored:
            self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in {'script', 'style'} and self.ignored:
            self.ignored -= 1
    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)

def _join_parts(parts):
    texts, locations = [], []
    offset = 0
    for label, text in parts:
        if texts:
            offset += 1
        locations.append(Location(label, offset, offset + len(text)))
        texts.append(text)
        offset += len(text)
    return '\n'.join(texts), tuple(locations)

def _media_type(source):
    media = (source.media_type or '').lower()
    if media in {'', 'application/octet-stream'} and source.kind == 'attachment':
        extension = source.name.rsplit('.', 1)[-1].lower()
        media = {'txt': 'text/plain', 'csv': 'text/csv', 'html': 'text/html', 'htm': 'text/html', 'pdf': 'application/pdf',
                 'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                 'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}.get(extension, media)
    return media


def extract(source, limits=ReadLimits()):
    content = source.content
    if content is None:
        raise ValueError('No local attachment content is available')
    if len(content) > limits.max_bytes:
        raise ValueError(f'Source exceeds byte budget ({limits.max_bytes})')
    media = _media_type(source)
    if media in {'text/plain', 'text/csv', 'text/html'}:
        text = content.decode(source.charset or 'utf-8-sig')
        if '\x00' in text:
            raise ValueError('Binary content in a declared text attachment requires manual review')
        if media == 'text/html':
            parser = _VisibleHtml()
            parser.feed(text)
            text = ''.join(parser.parts).strip()
            if parser.login_form or re.search(r'(?:sign in|log in|login) to (?:continue|view|access)|(?:enable javascript|javascript is required)', text, re.IGNORECASE):
                raise ValueError('Page requires login or JavaScript rendering; manual review is required')
            if not text and parser.ignored == 0:
                raise ValueError('Page has no visible text; login or JavaScript rendering requires manual review')
        return text, (Location('text', 0, len(text)),)
    if media == 'application/pdf':
        try:
            from pypdf import PdfReader
            from pypdf.errors import PyPdfError
        except ImportError as exc:
            raise ValueError('PDF support requires pypdf; reinstall ActionMail') from exc
        try:
            reader = PdfReader(io.BytesIO(content), strict=False)
            if reader.is_encrypted:
                raise ValueError('Encrypted PDF requires manual review')
            if len(reader.pages) > 100:
                raise ValueError('PDF exceeds the 100-page budget')
            parts = []
            for index, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ''
                if not text.strip():
                    raise ValueError(f'PDF page {index} has no extractable text; image-only content requires manual review')
                parts.append((f'page:{index}', text))
            return _join_parts(parts)
        except PyPdfError as exc:
            raise ValueError('PDF could not be read') from exc
    kinds = {
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    }
    if media in kinds:
        return _join_parts(office_parts(content, kinds[media]))
    raise ValueError(f'Unsupported attachment type: {media or "unknown"}')

def _text_from_bytes(source):
    return extract(source)[0]

def read_external_sources(email: EmailPackage, *, fetch_live=None, selected_ids=None, limits=ReadLimits()) -> ReadOutcome:
    sources = [s for s in email.external_sources if selected_ids is None or s.source_id in selected_ids]
    if len(sources) > limits.max_sources:
        return ReadOutcome(email, (), (f'External source budget exceeded: unread IDs {[s.source_id for s in sources]}',))
    read, records, failures, pending = [], [], [], []
    total = 0
    for source in sources:
        try:
            final_url = retrieved_at = None
            media = _media_type(source) or None
            charset = source.charset
            replay = None
            if source.snapshot_text is not None:
                content = source.snapshot_text.encode('utf-8')
                method = 'frozen_snapshot'
                text = source.snapshot_text
                locations = (Location('snapshot', 0, len(text)),)
            elif source.kind == 'attachment':
                content = source.content or b''
                method = 'local_attachment'
                text, locations = extract(source, limits)
            elif source.kind == 'link' and fetch_live is not None:
                fetched = fetch_live(source.name)
                content, media, charset = fetched
                final_url = getattr(fetched, 'final_url', None)
                retrieved_at = getattr(fetched, 'retrieved_at', None)
                replay = base64.b64encode(content).decode('ascii')
                method = 'allowlisted_https'
                text, locations = extract(replace(source, content=content, media_type=media, charset=charset), limits)
            else:
                raise ValueError('No approved snapshot or live reader is available')
            if len(content) > limits.max_bytes:
                raise ValueError(f'Source exceeds byte budget ({limits.max_bytes})')
            if not text.strip():
                raise ValueError('Source contains no extractable text')
            if len(text) > limits.max_text_chars or total + len(text) > limits.max_total_chars:
                raise ValueError(f'Extracted-content budget exceeded; {len(text)} characters unread')
            total += len(text)
            read.append(SourceText(source.source_id, text))
            extraction_method = 'snapshot_text' if method == 'frozen_snapshot' else {
                'application/pdf': 'pypdf_text_pages',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'ooxml_paragraphs',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'ooxml_sheet_cells',
                'text/html': 'visible_html_parser',
            }.get(media, 'declared_charset_text')
            records.append(ReadRecord(source.source_id, source.name, method, hashlib.sha256(content).hexdigest(),
                                      len(text), len(content), media, final_url, retrieved_at, locations, text, replay, extraction_method, charset))
        except (OSError, UnicodeError, ValueError, LookupError, http.client.HTTPException) as exc:
            pending.append(source.name)
            failures.append(f'{source.source_id}: {exc}')
    return ReadOutcome(replace(email, read_sources=tuple(read), unread_sources=tuple(pending)), tuple(records), tuple(failures))
