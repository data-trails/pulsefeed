"""Bounded HTTP requests, date parsing and meeting-body scoping."""
from datetime import datetime, timezone
import re
from urllib.parse import unquote, urlparse

import requests

HEADERS = {'User-Agent': 'PulseFeed/1.0 (planning-commission public-records monitor)'}
SESSION = requests.Session()
_diagnostics = []
_requests = 0
_successes = 0


def begin_source():
    global _requests, _successes
    _diagnostics.clear()
    _requests = _successes = 0


def record_issue(message):
    _diagnostics.append(message)


def source_diagnostics():
    return {'requests': _requests, 'successfulRequests': _successes,
            'issues': list(dict.fromkeys(_diagnostics))}


def request_bytes(url, max_bytes=5 * 1024 * 1024):
    global _requests, _successes
    _requests += 1
    try:
        with SESSION.get(url, timeout=(10, 20), headers=HEADERS, stream=True) as response:
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError(f'HTTP {response.status_code}: document content not available')
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError(f'Response exceeds {max_bytes // (1024 * 1024)} MiB limit')
                chunks.append(chunk)
            raw = b''.join(chunks)
            _successes += 1
            return raw, response.url
    except (requests.RequestException, ValueError) as exc:
        record_issue(f'{url}: {exc}')
        return None, url


MONTH = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'


def parse_date(text):
    text = re.sub(r'\bSept\b', 'Sep', unquote(text or ''), flags=re.I)
    # Process basenames without destroying numeric date separators.
    for pattern, order in [
        (r'(?<!\d)(20\d{2})[-_.](\d{1,2})[-_.](\d{1,2})(?!\d)', 'ymd'),
        (r'(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)', 'ymd'),
        (r'(?<!\d)(\d{1,2})[-_./](\d{1,2})[-_./](20\d{2}|\d{2})(?!\d)', 'mdy'),
    ]:
        for match in re.finditer(pattern, text):
            a, b, c = map(int, match.groups())
            year, month, day = (a, b, c) if order == 'ymd' else (c + 2000 if c < 100 else c, a, b)
            try:
                return datetime(year, month, day, tzinfo=timezone.utc)
            except ValueError:
                continue
    normal = re.sub(r'[-_]', ' ', text)
    normal = re.sub(r'(\d)(?:st|nd|rd|th)\b', r'\1', normal, flags=re.I)
    for pattern, formats in [
        (rf'\b{MONTH}\.?\s+\d{{1,2}},?\s+20\d{{2}}\b', ('%B %d %Y', '%b %d %Y')),
        (rf'\b20\d{{2}}\s+{MONTH}\.?\s+\d{{1,2}}\b', ('%Y %B %d', '%Y %b %d')),
    ]:
        for match in re.finditer(pattern, normal, re.I):
            value = re.sub(r'\s+', ' ', match.group().replace(',', '').replace('.', ''))
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
    return None


def link_date(anchor):
    # Prefer a document's own date to a sibling meeting or upload-folder date.
    filename = urlparse(anchor.get('href', '')).path.rsplit('/', 1)[-1]
    values = [filename, anchor.get_text(' ', strip=True)]
    dates = [date for value in values if (date := parse_date(value))]
    if len({d.date() for d in dates}) > 1:
        record_issue(f'Conflicting document dates: {anchor.get("href", "")}')
        return None
    if dates:
        return dates[0]
    row = anchor.find_parent(['li', 'p', 'tr'])
    if row and len(row.get_text()) < 1000:
        return parse_date(row.get_text(' ', strip=True))
    return None


def document_link(url):
    parsed = urlparse(url)
    path = parsed.path.lower()
    return (path.endswith('.pdf') or '/pdf/' in path or
            '/agendacenter/viewfile/' in path or
            bool(re.search(r'(?:^|&)(?:ddownload|download)=', parsed.query, re.I)) or
            path.rstrip('/').endswith('/file'))


PC = re.compile(r'planning[\s_/-]*(?:commission|board)|(?:^|[\W_])pc(?:[\W_]|$)', re.I)
OTHER_BODY = re.compile(r'city[\s_-]*council|township[\s_-]*board|board[\s_-]*of[\s_-]*(?:trustees|public|light)|\b(?:zba|bpw|edc|bra)\b', re.I)


def planning_link(anchor, page_url):
    direct = unquote(anchor.get('href', '') + ' ' + anchor.get_text(' ', strip=True))
    if PC.search(direct):
        return True
    if OTHER_BODY.search(direct):
        return False
    row = anchor.find_parent('tr') or anchor.find_parent('li')
    if row:
        context = row.get_text(' ', strip=True)
        if OTHER_BODY.search(context):
            return False
        if PC.search(context):
            return True
    # A section heading can scope a mixed archive, but must be the nearest heading.
    heading = anchor.find_previous(['h2', 'h3', 'h4'])
    if heading:
        context = heading.get_text(' ', strip=True)
        if OTHER_BODY.search(context):
            return False
        if PC.search(context):
            return True
    # Dedicated archive URLs establish body; a fragment on a mixed page does not.
    return bool(PC.search(unquote(urlparse(page_url).path)))
