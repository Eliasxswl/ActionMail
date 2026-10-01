"""One private SQLite store. Each update is committed before external effects."""
import base64
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from actionmail.domain.email import EmailPackage, ExternalSource, SourceText


def encode_email(email):
    value = asdict(email)
    value['received_at'] = email.received_at.isoformat() if email.received_at else None
    for source in value['external_sources']:
        if source['content'] is not None:
            source['content'] = base64.b64encode(source['content']).decode('ascii')
    return value


def decode_email(value):
    value = dict(value)
    value['received_at'] = datetime.fromisoformat(value['received_at']) if value['received_at'] else None
    for key in ('thread', 'read_sources'):
        value[key] = tuple(SourceText(**source) for source in value[key])
    external = []
    for source in value['external_sources']:
        source = dict(source)
        if source['content'] is not None:
            source['content'] = base64.b64decode(source['content'])
        external.append(ExternalSource(**source))
    value['external_sources'] = tuple(external)
    for key in ('recipients', 'to_recipients', 'cc_recipients', 'unread_sources'):
        value[key] = tuple(value[key])
    return EmailPackage(**value)


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, identity TEXT UNIQUE NOT NULL, data TEXT NOT NULL)')

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def all(self):
        with self._connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT data FROM records ORDER BY rowid DESC')]

    def get(self, record_id):
        with self._connect() as db:
            row = db.execute('SELECT data FROM records WHERE id=?', (record_id,)).fetchone()
        if row is None:
            raise KeyError('Message not found')
        return json.loads(row[0])

    def find(self, identity):
        with self._connect() as db:
            row = db.execute('SELECT data FROM records WHERE identity=?', (identity,)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, value):
        with self._connect() as db:
            db.execute('INSERT INTO records VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                       (value['id'], value['identity'], json.dumps(value, ensure_ascii=False)))
