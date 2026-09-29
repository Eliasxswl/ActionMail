import http.client
import ipaddress
import re
import socket
import ssl
from urllib.parse import urljoin, urlsplit

from actionmail.content.reader import MAX_SOURCE_BYTES


REDIRECT_CODES = {301, 302, 303, 307, 308}
SUPPORTED_MEDIA_TYPES = {"text/plain", "text/csv", "text/html", "application/pdf"}


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, address: str) -> None:
        super().__init__(hostname, timeout=10, context=ssl.create_default_context())
        self._verified_address = address

    def connect(self) -> None:
        plain_socket = socket.create_connection((self._verified_address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(plain_socket, server_hostname=self.host)
        except Exception:
            plain_socket.close()
            raise


def _destination(url: str, allowed_domains: set[str]) -> tuple[str, str, str]:
    if any(character.isspace() or ord(character) < 32 for character in url):
        raise ValueError("Link contains whitespace or a control character")
    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https" or not hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("Only HTTPS links without embedded credentials are allowed")
    if parsed.fragment:
        raise ValueError("Link fragments are not supported")
    if parsed.port not in {None, 443}:
        raise ValueError("Only the standard HTTPS port is allowed")
    if hostname not in allowed_domains:
        raise ValueError("Link domain is not in the explicit allowlist")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ValueError("IP-address links are not allowed")
    addresses = {
        info[4][0]
        for info in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    }
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Link domain resolves to a non-public address")
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return hostname, sorted(addresses)[0], path


def fetch_allowlisted_https(url: str, allowed_domains: tuple[str, ...]) -> tuple[bytes, str, str | None]:
    """Fetch a public HTTPS page through a DNS-pinned, allowlisted connection."""
    allowed = {domain.lower().strip() for domain in allowed_domains}
    if not allowed:
        raise ValueError("No live-link domains were explicitly allowed")
    current = url
    for redirect_count in range(3):
        hostname, address, path = _destination(current, allowed)
        connection = _PinnedHTTPSConnection(hostname, address)
        try:
            connection.request("GET", path, headers={
                "Host": hostname,
                "Accept": "text/plain, text/html, text/csv, application/pdf",
                "Accept-Encoding": "identity",
                "User-Agent": "ActionMail/2.0",
            })
            response = connection.getresponse()
            if response.status in REDIRECT_CODES:
                location = response.getheader("Location")
                if not location or redirect_count == 2:
                    raise ValueError("Link redirect is missing or exceeds the two-redirect limit")
                current = urljoin(current, location)
                continue
            if response.status != 200:
                raise ValueError(f"Link returned HTTP {response.status}")
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                raise ValueError("Compressed link responses are not supported")
            content_type = response.getheader("Content-Type", "").split(";", 1)
            media_type = content_type[0].strip().lower()
            if media_type not in SUPPORTED_MEDIA_TYPES:
                raise ValueError(f"Unsupported link content type: {media_type or 'unknown'}")
            charset = None
            if len(content_type) == 2:
                match = re.search(r"charset\s*=\s*([^;]+)", content_type[1], re.IGNORECASE)
                if match:
                    charset = match.group(1).strip().strip('"')
            content = response.read(MAX_SOURCE_BYTES + 1)
            if len(content) > MAX_SOURCE_BYTES:
                raise ValueError("Link response exceeds the 2 MiB limit")
            return content, media_type, charset
        finally:
            connection.close()
    raise ValueError("Link redirect limit exceeded")
