from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
import re

from actionmail.domain.email import EmailPackage


class _TextFromHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.links: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.ignored_depth += 1
        if tag == "a":
            href = dict(attrs).get("href")
            if href and href.startswith(("https://", "http://")):
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)


def _body_content(message) -> tuple[str, tuple[str, ...]]:
    html_links = []
    for item in message.walk():
        if item.get_content_type() == "text/html" and item.get_content_disposition() != "attachment":
            parser = _TextFromHtml()
            parser.feed(item.get_content())
            html_links.extend(parser.links)
    part = message.get_body(preferencelist=("plain", "html"))
    if part is None:
        return "", tuple(dict.fromkeys(html_links))
    content = part.get_content()
    if part.get_content_type() == "text/html":
        parser = _TextFromHtml()
        parser.feed(content)
        return " ".join(parser.parts).strip(), tuple(dict.fromkeys(html_links))
    links = re.findall(r"https?://[^\s<>\"']+", content)
    return content.strip(), tuple(dict.fromkeys((*links, *html_links)))


def load_eml(path: Path, target_recipient: str) -> EmailPackage:
    with path.open("rb") as stream:
        message = BytesParser(policy=policy.default).parse(stream)

    date_header = message.get("Date")
    if not date_header:
        raise ValueError("The email has no Date header")
    received_at = parsedate_to_datetime(date_header)
    to_recipients = tuple(address for _, address in getaddresses(message.get_all("To", [])))
    cc_recipients = tuple(address for _, address in getaddresses(message.get_all("Cc", [])))
    recipients = tuple(dict.fromkeys((*to_recipients, *cc_recipients)))
    attachments = tuple(part.get_filename() or "unnamed attachment" for part in message.iter_attachments())
    body, links = _body_content(message)

    return EmailPackage(
        case_id=path.stem,
        target_recipient=target_recipient,
        received_at=received_at,
        sender=str(message.get("From", "")),
        recipients=recipients,
        to_recipients=to_recipients,
        cc_recipients=cc_recipients,
        subject=str(message.get("Subject", "")),
        body=body,
        unread_sources=tuple(dict.fromkeys((*attachments, *links))),
    )
