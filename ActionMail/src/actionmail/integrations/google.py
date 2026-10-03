"""Injectable bounded Google REST transport. No implicit write retries."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class UnknownWrite(RuntimeError):
    """The request may have reached Google. Reconcile before attempting a write."""


class GoogleTransport:
    def __init__(self, token_source):
        self.token_source = token_source

    def request(self, method, url, body=None):
        # Adapters own URLs. Never accept an arbitrary endpoint from email/model data.
        if not url.startswith(('https://gmail.googleapis.com/gmail/v1/',
                               'https://www.googleapis.com/calendar/v3/')):
            raise ValueError('Unsupported Google endpoint')
        request = Request(url, method=method,
                          data=json.dumps(body).encode() if body is not None else None,
                          headers={'Authorization': 'Bearer ' + self.token_source.access_token(),
                                   'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=30) as response:
                data = response.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024:
                raise ValueError('Provider response exceeds the byte limit')
            result = json.loads(data)
            if not isinstance(result, dict):
                raise ValueError('Provider response must be an object')
            return result
        except HTTPError as exc:
            if method != 'GET' and exc.code >= 500:
                raise UnknownWrite('Calendar outcome unknown; reconcile before retry') from exc
            message = {401: 'Authorization expired; reconnect the account',
                       403: 'Permission denied; check granted scopes',
                       404: 'Provider resource not found', 409: 'Event ID already exists'}.get(exc.code,
                       f'Google returned HTTP {exc.code}')
            raise ProviderError(exc.code, message) from exc
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            if method != 'GET':
                raise UnknownWrite('Calendar outcome unknown; reconcile before retry') from exc
            raise ProviderError(0, 'Google connection or response failed') from exc
