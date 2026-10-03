"""Build and verify the final hand-in ZIP; exclude local state and historical archives.

Run from any directory. Only the four documented submission trees and root README
are included. The embedded manifest makes the archive independently inspectable.
"""
import hashlib
import json
import zipfile
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
OUTPUT = WORKSPACE / 'ActionMail-submission.zip'
EXCLUDED_DIRECTORIES = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache',
                        'build', 'dist', 'archive', 'private', 'tmp', '.ruff_cache'}


def included(relative):
    """Allow active hash-bound fixtures despite their historical directory name."""
    parts = list(relative.parts)
    if parts[:3] == ['ActionMail', 'evaluation', 'archive']:
        parts[2] = 'active-fixtures'
    if any(part in EXCLUDED_DIRECTORIES or part.endswith('.egg-info') for part in parts):
        return False
    name = relative.name.lower()
    return not (name.startswith('.env') or name.startswith('client_secret')
                or name == 'credentials.json' or name.endswith(('.pyc', '.log', '.sqlite3',
                                                               '.demo-events.json', '-token.json', '-token.tmp'))
                or '.sqlite3-' in name)


def main():
    paths = [WORKSPACE / 'README.md']
    for name in ('ActionMail', 'experiments', 'report', 'data'):
        paths.extend(path for path in (WORKSPACE / name).rglob('*')
                     if path.is_file() and included(path.relative_to(WORKSPACE)))
    paths = sorted(paths)
    records = [{'path': path.relative_to(WORKSPACE).as_posix(), 'bytes': path.stat().st_size,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths]
    temporary = OUTPUT.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, record in zip(paths, records):
            archive.write(path, record['path'])
        archive.writestr('SUBMISSION_MANIFEST.json', json.dumps({
            'purpose': 'Final PE6201 ActionMail submission',
            'measured_business_commit': 'c405d2901ff1577ebafbc2a3ff151654970bb7ea',
            'files': records}, indent=2))
    with zipfile.ZipFile(temporary) as archive:
        assert archive.testzip() is None
        for record in records:
            assert hashlib.sha256(archive.read(record['path'])).hexdigest() == record['sha256'], record['path']
    # Atomic publication only after checking the complete ZIP.
    temporary.replace(OUTPUT)
    OUTPUT.with_suffix('.zip.sha256').write_text(
        hashlib.sha256(OUTPUT.read_bytes()).hexdigest() + '  ' + OUTPUT.name + '\n', encoding='ascii')
    print(f'Created {OUTPUT.name}: {len(records)} verified files, {OUTPUT.stat().st_size:,} bytes.')


if __name__ == '__main__':
    main()
