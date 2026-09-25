"""Compile the governed workbook into the registry shared by Python and React."""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / 'config/pulsefeed_master_sources.xlsx'
REGISTRY = ROOT / 'config/sources.json'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
GROUPS = {
    'RSS_SOURCES': ('rss_html', {'rss', 'url'}),
    'MANUAL_SOURCES': ('manual', {'url'}),
    'JOOMLA_SOURCES': ('joomla', set()),
    'CIVICPLUS_SOURCES': ('civicplus', {'agenda_center_url', 'base_url'}),
}
STATUSES = {'Production', 'Ready for Testing', 'Adapter Needed',
            'Manual Setup Needed', 'Source Verification Needed'}


def read_tables(path):
    with zipfile.ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(t.itertext()) for t in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        relationships = {r.get('Id'): r.get('Target') for r in
                         ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        tables = {}
        for sheet in ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets', NS):
            target = relationships[sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            member = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            rows = []
            for row in ET.fromstring(z.read(member)).findall('.//s:sheetData/s:row', NS):
                values = []
                for cell in row:
                    if cell.find('s:f', NS) is not None:
                        raise ValueError(f"Formula not allowed: {sheet.get('name')}!{cell.get('r')}")
                    col = 0
                    for char in re.match(r'[A-Z]+', cell.get('r')).group():
                        col = col * 26 + ord(char) - 64
                    value = cell.find('s:v', NS)
                    inline = cell.find('s:is', NS)
                    text = (value.text or '') if value is not None else ''.join(inline.itertext()) if inline is not None else ''
                    if cell.get('t') == 's':
                        text = strings[int(text)]
                    values.extend([''] * (col - len(values)))
                    values[col - 1] = text
                if any(values):
                    rows.append(values)
            if rows:
                tables[sheet.get('name')] = [dict(zip(rows[0], r + [''] * (len(rows[0]) - len(r)))) for r in rows[1:]]
        return tables


def valid_url(value, allow_blank=False):
    if allow_blank and value == '':
        return
    parsed = urlparse(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f'Invalid public URL: {value!r}')


def compile_registry(tables):
    rows = tables['Active Sources']
    identities = set()
    names = set()
    for row in rows:
        identity = row['Source ID']
        if not identity or identity in identities:
            raise ValueError(f'Missing or duplicate Source ID: {identity}')
        identities.add(identity)
        if not all(row[key] for key in ('County', 'Local Unit', 'Meeting Body')):
            raise ValueError(f'Missing source identity: {identity}')
    endpoints = {}
    endpoint_ids = set()
    for endpoint in tables['Source Endpoints']:
        key = endpoint['Endpoint ID']
        if not key or key in endpoint_ids:
            raise ValueError(f'Missing or duplicate endpoint ID: {key}')
        endpoint_ids.add(key)
        if endpoint['Source ID'] not in identities:
            raise ValueError(f'Orphan endpoint: {key}')
        if endpoint['Production Status'] == 'Production':
            endpoints.setdefault(endpoint['Source ID'], []).append(endpoint)
    output = []
    for row in rows:
        identity = row['Source ID']
        status = row['Deployment Status']
        if status not in STATUSES:
            raise ValueError(f'Unknown deployment status: {identity}: {status}')
        valid_url(row['Public Source URL'])
        source = {
            'id': identity, 'county': row['County'], 'name': row['Legacy Source Name'] or f"{row['Local Unit']} {row['Meeting Body']}",
            'meetingBody': row['Meeting Body'], 'url': row['Public Source URL'],
            'deploymentStatus': status, 'handler': 'manual',
            'notes': row['Notes'], 'endpoints': {},
        }
        name_key = (source['county'], source['name'])
        if name_key in names:
            raise ValueError(f'Duplicate runtime identity: {name_key}')
        names.add(name_key)
        eps = endpoints.get(identity, [])
        if status != 'Production':
            if eps:
                raise ValueError(f'Production endpoints for inactive source: {identity}')
            source['handler'] = 'candidate'
        else:
            if not row['Legacy Source Name'] or not eps:
                raise ValueError(f'Missing production identity/endpoints: {identity}')
            groups = {e['JSON Group'] for e in eps}
            if len(groups) != 1 or not groups.issubset(GROUPS):
                raise ValueError(f'Unsupported/mixed handler groups: {identity}')
            handler, fields = GROUPS[next(iter(groups))]
            source['handler'] = handler
            ordered = sorted(eps, key=lambda e: int(e['Endpoint Order']))
            if len({e['Endpoint Order'] for e in ordered}) != len(ordered):
                raise ValueError(f'Duplicate endpoint order: {identity}')
            for e in ordered:
                field, value = e['JSON Field'], e['URL']
                expected = 'html' if handler == 'rss_html' and field == 'url' else handler
                if e['Handler Type'] != expected:
                    raise ValueError(f'Handler disagreement: {identity}')
                if field in source['endpoints']:
                    raise ValueError(f'Duplicate endpoint field: {identity}: {field}')
                valid_url(value, allow_blank=field == 'rss')
                source['endpoints'][field] = value
            if handler == 'rss_html':
                source['endpoints'].setdefault('rss', '')
            if handler == 'joomla':
                keys = list(source['endpoints'])
                if keys != [f'pages[{i}]' for i in range(len(keys))]:
                    raise ValueError(f'Invalid Joomla page ordering: {identity}')
                source['endpoints'] = {'pages': list(source['endpoints'].values())}
            elif set(source['endpoints']) != fields:
                raise ValueError(f'Missing or unsupported endpoint fields: {identity}')
            if handler == 'rss_html' and source['endpoints']['rss'] != row['Production RSS URL']:
                raise ValueError(f'RSS mismatch: {identity}')
        output.append(source)
    return output


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
    if path.exists() and path.read_text() == content:
        return
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as f:
        temporary = f.name
        f.write(content)
    try:
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    registry = compile_registry(read_tables(WORKBOOK))
    if args.write:
        atomic_json(REGISTRY, registry)
    elif not REGISTRY.exists() or json.loads(REGISTRY.read_text()) != registry:
        raise SystemExit('Registry differs from workbook. Run python scraper/source_workbook.py --write')
    print(f'{len(registry)} sources validated; {sum(s["deploymentStatus"] == "Production" for s in registry)} configured in production.')


if __name__ == '__main__':
    main()
