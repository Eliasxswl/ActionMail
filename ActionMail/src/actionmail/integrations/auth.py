"""Desktop OAuth is explicitly invoked, separately for mail and calendar."""
import argparse
import os
import sys
from pathlib import Path

from actionmail.integrations.google import ProviderError

SCOPES = {
    'gmail': ['https://www.googleapis.com/auth/gmail.readonly'],
    'calendar': ['https://www.googleapis.com/auth/calendar.events.owned',
                 'https://www.googleapis.com/auth/calendar.calendarlist.readonly'],
}


def private_home():
    return Path(os.environ.get('ACTIONMAIL_PRIVATE_DIR') or
                str(Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local/share'))) / 'ActionMail'))


class GoogleAuth:
    def __init__(self, feature, directory=None):
        if feature not in SCOPES:
            raise ValueError('Unknown Google feature')
        self.feature = feature
        self.directory = Path(directory) if directory else private_home()
        self.path = self.directory / (feature + '-token.json')

    def _save(self, credentials):
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(credentials.to_json(), encoding='utf-8')
        if os.name != 'nt':
            temporary.chmod(0o600)
        temporary.replace(self.path)

    def connect(self, client_file):
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(str(client_file), SCOPES[self.feature])
        credentials = flow.run_local_server(host='127.0.0.1', port=0, timeout_seconds=180)
        if not credentials.has_scopes(SCOPES[self.feature]):
            raise ProviderError(403, 'Required permissions were not granted')
        self._save(credentials)

    def access_token(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        if not self.path.exists():
            raise ProviderError(401, 'Connect this Google feature first')
        try:
            credentials = Credentials.from_authorized_user_file(str(self.path))
            if not credentials.has_scopes(SCOPES[self.feature]):
                raise ProviderError(403, 'Reconnect with the required permissions')
            if not credentials.valid:
                credentials.refresh(Request())
                self._save(credentials)
            return credentials.token
        except ProviderError:
            raise
        except Exception as exc:
            # Never expose credential contents or Google's raw error response.
            raise ProviderError(401, 'Token refresh failed; reconnect the account') from exc

    def disconnect(self):
        self.path.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Explicit Google desktop authorization (network required).')
    parser.add_argument('operation', choices=['connect', 'disconnect'])
    parser.add_argument('feature', choices=list(SCOPES))
    parser.add_argument('--client-file', type=Path)
    args = parser.parse_args(argv)
    auth = GoogleAuth(args.feature)
    if args.operation == 'disconnect':
        auth.disconnect()
        print('Local credentials removed. Existing local tasks are retained.')
    else:
        if not args.client_file:
            parser.error('--client-file is required for connect')
        try:
            auth.connect(args.client_file)
        except ImportError:
            print('Install the optional Google dependencies with pip install -e ".[google]".', file=sys.stderr)
            return 1
        except Exception:
            print('Authorization failed or was denied. No account connection was established.', file=sys.stderr)
            return 1
        print('Authorization saved in local private storage.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
