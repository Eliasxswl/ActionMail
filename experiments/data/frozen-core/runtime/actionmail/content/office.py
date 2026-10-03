"""Bounded OOXML extraction. Relationships, formulas and objects are never executed."""
import io
import posixpath
import zipfile
from xml.etree import ElementTree as ET

MAX_EXPANDED_BYTES = 16 * 1024 * 1024
MAX_MEMBERS = 512
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def _archive(content):
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
        members = archive.infolist()
        if len(members) > MAX_MEMBERS or sum(m.file_size for m in members) > MAX_EXPANDED_BYTES:
            raise ValueError('Office archive exceeds expanded-content budget')
        names = [m.filename for m in members]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate Office archive members')
        for m in members:
            if m.flag_bits & 1 or m.filename.startswith('/') or '..' in m.filename.split('/'):
                raise ValueError('Encrypted or unsafe Office archive member')
            if m.file_size > 100 * max(m.compress_size, 1):
                raise ValueError('Office archive compression ratio exceeds budget')
            if 'vbaproject' in m.filename.lower() or '/embeddings/' in m.filename.lower():
                raise ValueError('Office macros or embedded objects require manual review')
        return archive
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise ValueError('Malformed or encrypted Office archive') from exc


def _xml(archive, name):
    try:
        data = archive.read(name)
        declarations = data.replace(b'\x00', b'').upper()
        if b'<!DOCTYPE' in declarations or b'<!ENTITY' in declarations:
            raise ValueError('XML declarations with entities are not supported')
        return ET.fromstring(data)
    except (KeyError, ET.ParseError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise ValueError(f'Malformed Office XML: {name}') from exc


def office_parts(content, kind):
    """Return ordered (location, text) pairs without resolving external relations."""
    with _archive(content) as archive:
        if kind == 'docx':
            root = _xml(archive, 'word/document.xml')
            parts = []
            for index, p in enumerate(root.iter(W + 'p'), 1):
                text = ''.join(n.text or '' if n.tag == W + 't' else '\t' if n.tag == W + 'tab' else '\n'
                               for n in p.iter() if n.tag in {W + 't', W + 'tab', W + 'br'})
                if text.strip():
                    parts.append((f'paragraph:{index}', text))
            # Headers/footers may contain current instructions; do not omit them.
            for name in sorted(archive.namelist()):
                if name.startswith(('word/header', 'word/footer', 'word/footnotes', 'word/endnotes')) and name.endswith('.xml'):
                    for index, p in enumerate(_xml(archive, name).iter(W + 'p'), 1):
                        text = ''.join(n.text or '' for n in p.iter(W + 't'))
                        if text.strip():
                            parts.append((f'{name}:paragraph:{index}', text))
            return parts
        workbook = _xml(archive, 'xl/workbook.xml')
        if workbook.find(S + 'workbookProtection') is not None:
            raise ValueError('Protected workbook requires manual review')
        relations = {r.attrib['Id']: r for r in _xml(archive, 'xl/_rels/workbook.xml.rels')}
        shared = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            shared = [''.join(t.text or '' for t in si.iter(S + 't')) for si in _xml(archive, 'xl/sharedStrings.xml')]
        parts = []
        for sheet in workbook.iter(S + 'sheet'):
            relation = relations.get(sheet.attrib.get(R + 'id'))
            if relation is None or relation.attrib.get('TargetMode') == 'External':
                raise ValueError('Missing or external spreadsheet sheet')
            target = relation.attrib.get('Target', '')
            name = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
            if not name.startswith('xl/') or '..' in name.split('/'):
                raise ValueError('Unsafe sheet relationship')
            root = _xml(archive, name)
            if root.find(S + 'sheetProtection') is not None:
                raise ValueError('Protected sheet requires manual review')
            for cell in root.iter(S + 'c'):
                location = f"sheet:{sheet.attrib['name']}!{cell.attrib.get('r', 'unknown')}"
                formula = cell.find(S + 'f')
                value = cell.find(S + 'v')
                text = value.text if value is not None and value.text is not None else ''
                if formula is not None:
                    text = f"formula (not executed): ={formula.text or ''}; cached value: {text or '[missing]'}"
                elif cell.attrib.get('t') == 's':
                    try:
                        index = int(text)
                        if index < 0:
                            raise ValueError('Negative shared-string reference')
                        text = shared[index]
                    except (ValueError, IndexError) as exc:
                        raise ValueError('Invalid shared-string reference') from exc
                elif cell.attrib.get('t') == 'inlineStr':
                    text = ''.join(t.text or '' for t in cell.iter(S + 't'))
                if text:
                    parts.append((location, text))
        return parts
