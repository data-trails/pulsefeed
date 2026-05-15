"""
PulseFeed scraper — fetches planning commission RSS feeds, scrapes HTML source
pages for upcoming meetings, and parses linked PDFs for agenda item summaries.
Writes results to public/feed.json.

Run locally:  python scraper/scrape.py
"""

import hashlib
import io
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import feedparser
import pdfplumber
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# RSS sources (WordPress /feed/ — confirmed to expose RSS)
# ---------------------------------------------------------------------------

RSS_SOURCES = [
    # Allegan County
    {"county": "Allegan", "name": "Allegan Township Planning Commission",
     "rss": "https://allegantownship.org/feed/",
     "url": "https://allegantownship.org/planning-commission/"},
    {"county": "Allegan", "name": "Fillmore Township Planning Commission",
     "rss": "https://fillmoretownship.org/feed/",
     "url": "https://fillmoretownship.org/board-minutes/"},
    {"county": "Allegan", "name": "Gun Plain Township Planning Commission",
     "rss": "https://www.gunplain.org/feed/",
     "url": "https://www.gunplain.org/meeting-minutes-and-agendas/"},
    {"county": "Allegan", "name": "Heath Township Planning Commission",
     "rss": "https://heathtownship.net/feed",
     "url": "https://heathtownship.net/"},
    {"county": "Allegan", "name": "Hopkins Township Planning Commission",
     "rss": "https://www.hopkinstownship.org/feed",
     "url": "https://www.hopkinstownship.org/board-minutes/"},
    {"county": "Allegan", "name": "Laketown Township Planning Commission",
     "rss": "https://laketowntwp.org/feed",
     "url": "https://laketowntwp.org/boards-commissions/"},
    {"county": "Allegan", "name": "Leighton Township Planning Commission",
     "rss": "https://leightontownship.org/feed/",
     "url": "https://leightontownship.org/meetings-minutes/"},
    {"county": "Allegan", "name": "Martin Township Planning Commission",
     "rss": "https://www.martintownship.org/feed",
     "url": "https://www.martintownship.org/"},
    {"county": "Allegan", "name": "Otsego Township Planning Commission",
     "rss": "https://www.otsegotownship.org/feed",
     "url": "https://www.otsegotownship.org/building-planning-and-zoning/"},
    {"county": "Allegan", "name": "Overisel Township Planning Commission",
     "rss": "https://overiseltownship.org/feed/",
     "url": "https://overiseltownship.org/planning-commission/"},
    {"county": "Allegan", "name": "Saugatuck Township Planning Commission",
     "rss": "https://saugatucktownshipmi.gov/feed",
     "url": "https://saugatucktownshipmi.gov/saugatuck-township-local-government/packets-agendas-minutes/agendas/"},
    {"county": "Allegan", "name": "Watson Township Planning Commission",
     "rss": "https://watsontownshipmi.gov/feed",
     "url": "https://watsontownshipmi.gov/"},
    {"county": "Allegan", "name": "Wayland Township Planning Commission",
     "rss": "https://waytwp.org/feed/",
     "url": "https://waytwp.org/departments/zoning/"},

    # Ottawa County
    {"county": "Ottawa", "name": "Allendale Charter Township Planning Commission",
     "rss": "https://allendalemi.gov/feed/",
     "url": "https://allendalemi.gov/planning-commission/"},
    {"county": "Ottawa", "name": "Blendon Township Planning Commission",
     "rss": "https://www.blendontownship-mi.gov/feed/",
     "url": "https://www.blendontownship-mi.gov/planning-commission/"},
    {"county": "Ottawa", "name": "Chester Township Planning Commission",
     "rss": "https://www.chester-twp.org/feed",
     "url": "https://www.chester-twp.org/documents/"},
    {"county": "Ottawa", "name": "Grand Haven Charter Township Planning Commission",
     "rss": "https://ghtmi.gov/feed",
     "url": "https://ghtmi.gov/boards/planning-commission/"},
    {"county": "Ottawa", "name": "Jamestown Charter Township Planning Commission",
     "rss": "https://twp.jamestown.mi.us/feed/",
     "url": "https://twp.jamestown.mi.us/government/boards-and-minutes/planning-commission-agendas-minutes/"},
    {"county": "Ottawa", "name": "Olive Township Planning Commission",
     "rss": "https://www.olivetownship.org/feed",
     "url": "https://www.olivetownship.org/document-category/pcminutes/"},
    {"county": "Ottawa", "name": "Polkton Charter Township Planning Commission",
     "rss": "https://polktontownship.com/feed/",
     "url": "https://polktontownship.com/planning-commission/"},
    {"county": "Ottawa", "name": "Port Sheldon Township Planning Commission",
     "rss": "https://www.portsheldontwp.org/feed",
     "url": "https://www.portsheldontwp.org/planning-commission/"},
    {"county": "Ottawa", "name": "Robinson Township Planning Commission",
     "rss": "https://robinsontwpmi.gov/feed",
     "url": "https://robinsontwpmi.gov/"},
    {"county": "Ottawa", "name": "Spring Lake Township Planning Commission",
     "rss": "https://springlaketwp.org/feed/",
     "url": "https://springlaketwp.org/board/planning-commission/"},
    {"county": "Ottawa", "name": "Tallmadge Charter Township Planning Commission",
     "rss": "https://tallmadge.com/feed/",
     "url": "https://tallmadge.com/minutes-agendas/"},
    {"county": "Ottawa", "name": "Wright Township Planning Commission",
     "rss": "http://wrighttownshipottawami.gov/feed",
     "url": "http://wrighttownshipottawami.gov/"},
]

# ---------------------------------------------------------------------------
# Keyword filter
# ---------------------------------------------------------------------------

KEYWORDS = {
    "planning commission", "planning", "agenda", "minutes",
    "public hearing", "zoning", "variance", "site plan", "special use",
}

PDF_KEYWORDS = {"agenda", "minutes", "planning", "zoning", "variance"}

SIX_MONTHS_SECONDS = 60 * 60 * 24 * 183

# ---------------------------------------------------------------------------
# HTTP config
# ---------------------------------------------------------------------------

HEADERS = {"User-Agent": "PulseFeed/1.0 (planning-commission public-records monitor)"}
REQUEST_TIMEOUT = 15
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB

# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------

DATE_RE = re.compile(
    r'\b(?:January|February|March|April|May|June|July|August|September|'
    r'October|November|December)\s+\d{1,2},?\s+\d{4}'
    r'|\b\d{1,2}/\d{1,2}/\d{4}'
    r'|\b\d{4}-\d{2}-\d{2}\b',
    re.IGNORECASE,
)
AGENDA_ITEM_RE = re.compile(r'^\s*(\d+[\.\)]\s+|[A-Z][\.\)]\s+|[•\-\*]\s+)')
AGENDA_START_RE = re.compile(r'\bAGENDA\b', re.IGNORECASE)
AGENDA_END_RE = re.compile(r'\b(ADJOURNMENT|EXECUTIVE SESSION)\b', re.IGNORECASE)
WHITESPACE_RE = re.compile(r'\s+')
HTML_TAG_RE = re.compile(r'<[^>]+>')

# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------

def is_relevant(title: str, summary: str) -> bool:
    combined = (title + " " + summary).lower()
    return any(kw in combined for kw in KEYWORDS)


def is_within_window(dt: datetime | None) -> bool:
    if dt is None:
        return True
    cutoff = datetime.now(timezone.utc).timestamp() - SIX_MONTHS_SECONDS
    return dt.timestamp() >= cutoff


def make_id(source: dict, entry_link: str) -> str:
    key = f"{source['county']}-{source['name']}-{entry_link}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def format_display_date(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.strftime("%a, %b %-d")


def classify_tag(dt: datetime | None) -> str:
    if not dt:
        return "New"
    return "Upcoming" if dt.date() >= datetime.now().date() else "Recent"


def strip_html(text: str) -> str:
    return HTML_TAG_RE.sub(" ", text or "").strip()


def clean(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text or "").strip()


def parse_flexible_date(date_str: str) -> datetime | None:
    date_str = date_str.strip()
    for fmt in ("%B %d, %Y", "%B %d %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None

# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def fetch_html(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as exc:
        print(f"    HTML fetch error {url}: {exc}")
        return None


def extract_pdf_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    seen: set[str] = set()
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        path = urlparse(href).path.lower()
        if path.endswith(".pdf") or "/pdf/" in path:
            full = urljoin(base_url, href)
            if full not in seen:
                seen.add(full)
                links.append(full)
    return links


def date_near_link(a_tag) -> str:
    """Search the link text and nearby DOM siblings/parent for a date string."""
    parts = [a_tag.get_text(" ", strip=True)]
    if a_tag.parent:
        parts.append(a_tag.parent.get_text(" ", strip=True))
    for sib in list(a_tag.previous_siblings)[:3]:
        if hasattr(sib, "get_text"):
            parts.append(sib.get_text(" ", strip=True))
    for sib in list(a_tag.next_siblings)[:3]:
        if hasattr(sib, "get_text"):
            parts.append(sib.get_text(" ", strip=True))
    m = DATE_RE.search(" ".join(parts))
    return m.group(0) if m else ""

# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------

def fetch_pdf_bytes(pdf_url: str) -> bytes | None:
    try:
        r = requests.get(pdf_url, timeout=REQUEST_TIMEOUT, headers=HEADERS, stream=True)
        r.raise_for_status()
        chunks: list[bytes] = []
        size = 0
        for chunk in r.iter_content(8192):
            size += len(chunk)
            if size > MAX_PDF_BYTES:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    except Exception as exc:
        print(f"    PDF fetch error {pdf_url}: {exc}")
        return None


def extract_agenda_items(text: str) -> str:
    """Pull numbered/bulleted agenda items from raw PDF text."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    items: list[str] = []
    in_agenda = False

    for line in lines:
        if AGENDA_START_RE.search(line):
            in_agenda = True
            continue
        if in_agenda and AGENDA_END_RE.search(line):
            items.append(line)
            break
        if AGENDA_ITEM_RE.match(line):
            items.append(line)
            if not in_agenda:
                in_agenda = True  # first numbered line triggers collection even without header

    if not items:
        # Fallback: first 10 numbered/bulleted lines anywhere in the doc
        for line in lines:
            if AGENDA_ITEM_RE.match(line) and len(line) > 5:
                items.append(line)
            if len(items) >= 10:
                break

    return "\n".join(items[:15])


def parse_pdf_agenda_items(pdf_url: str) -> str:
    raw = fetch_pdf_bytes(pdf_url)
    if not raw:
        return ""
    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages[:6])
    except Exception as exc:
        print(f"    PDF parse error {pdf_url}: {exc}")
        return ""
    return extract_agenda_items(text)


def is_pdf_relevant(pdf_url: str) -> bool:
    filename = urlparse(pdf_url).path.lower().split("/")[-1]
    return any(kw in filename for kw in PDF_KEYWORDS)

# ---------------------------------------------------------------------------
# RSS scraper
# ---------------------------------------------------------------------------

def scrape_rss(source: dict) -> list[dict]:
    items = []
    try:
        feed = feedparser.parse(source["rss"])
        for entry in feed.entries[:20]:
            title = clean(entry.get("title", ""))
            summary = clean(strip_html(entry.get("summary", "") or entry.get("description", "")))

            if not is_relevant(title, summary):
                continue

            published_tuple = entry.get("published_parsed") or entry.get("updated_parsed")
            dt = datetime(*published_tuple[:6], tzinfo=timezone.utc) if published_tuple else None

            if not is_within_window(dt):
                continue

            link = entry.get("link", source["url"])

            items.append({
                "id": make_id(source, link),
                "county": source["county"],
                "source": source["name"],
                "title": title or f"{source['name']} — new posting",
                "date": dt.strftime("%Y-%m-%d") if dt else "",
                "dateDisplay": format_display_date(dt),
                "time": "",
                "summary": summary[:400] if summary else "",
                "details": "",
                "link": link,
                "tag": classify_tag(dt),
                "scrapedAt": datetime.now(timezone.utc).isoformat(),
            })

    except Exception as exc:
        print(f"  ERROR {source['name']}: {exc}")

    return items


def enrich_with_pdf(item: dict) -> dict:
    """Add pdfItems to an RSS item by following its link to find and parse agenda PDFs."""
    link = item.get("link", "")
    if not link:
        return item

    if urlparse(link).path.lower().endswith(".pdf"):
        pdf_items = parse_pdf_agenda_items(link)
        if pdf_items:
            item["pdfItems"] = pdf_items
        return item

    # Visit the linked HTML page and find attached PDFs
    soup = fetch_html(link)
    if not soup:
        return item

    pdf_links = extract_pdf_links(soup, link)
    # Prefer PDFs with relevant filenames; fall back to any PDF
    ordered = sorted(pdf_links, key=lambda u: (0 if is_pdf_relevant(u) else 1))
    for pdf_url in ordered[:3]:
        pdf_items = parse_pdf_agenda_items(pdf_url)
        if pdf_items:
            item["pdfItems"] = pdf_items
            break

    return item

# ---------------------------------------------------------------------------
# HTML source scraper — finds PDFs not surfaced by RSS
# ---------------------------------------------------------------------------

def scrape_html_source(source: dict, existing_ids: set[str]) -> list[dict]:
    """Scrape the source page directly for agenda/minutes PDFs not in the RSS feed."""
    soup = fetch_html(source["url"])
    if not soup:
        return []

    items: list[dict] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        path = urlparse(href).path.lower()
        if not (path.endswith(".pdf") or "/pdf/" in path):
            continue
        if not is_pdf_relevant(urljoin(source["url"], href)):
            continue

        pdf_url = urljoin(source["url"], href)
        item_id = make_id(source, pdf_url)
        if item_id in existing_ids:
            continue

        date_str = date_near_link(a)
        dt = parse_flexible_date(date_str) if date_str else None
        if dt and not is_within_window(dt):
            continue

        link_text = clean(a.get_text(" ", strip=True))
        filename_title = (
            path.split("/")[-1]
            .replace("-", " ").replace("_", " ").replace(".pdf", "").title()
        )
        title = link_text or filename_title or f"{source['name']} — document"

        if not is_relevant(title, filename_title):
            continue

        print(f"    Parsing PDF: {pdf_url}")
        pdf_items = parse_pdf_agenda_items(pdf_url)
        time.sleep(0.5)

        existing_ids.add(item_id)
        items.append({
            "id": item_id,
            "county": source["county"],
            "source": source["name"],
            "title": title,
            "date": dt.strftime("%Y-%m-%d") if dt else "",
            "dateDisplay": format_display_date(dt),
            "time": "",
            "summary": pdf_items[:400] if pdf_items else "",
            "details": "",
            "link": pdf_url,
            "tag": classify_tag(dt),
            "pdfItems": pdf_items,
            "scrapedAt": datetime.now(timezone.utc).isoformat(),
        })

    return items

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

FEED_PATH = os.path.join(os.path.dirname(__file__), "..", "public", "feed.json")


def load_existing() -> list[dict]:
    try:
        with open(FEED_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def main():
    print(f"PulseFeed scraper — {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")
    existing = load_existing()
    existing_ids = {item["id"] for item in existing}

    all_new: list[dict] = []

    for source in RSS_SOURCES:
        print(f"  {source['name']}")

        # RSS pass
        rss_items = [i for i in scrape_rss(source) if i["id"] not in existing_ids]
        for item in rss_items:
            existing_ids.add(item["id"])
            print(f"    RSS item: {item['title'][:60]}")
            enrich_with_pdf(item)
            time.sleep(0.3)
        all_new.extend(rss_items)

        # HTML source pass — picks up PDFs not exposed by RSS
        html_items = scrape_html_source(source, existing_ids)
        print(f"    {len(rss_items)} RSS + {len(html_items)} HTML item(s)")
        all_new.extend(html_items)

        time.sleep(0.5)

    # Prune items that have aged out of the 6-month window
    existing = [i for i in existing if is_within_window(
        datetime.fromisoformat(i["date"]).replace(tzinfo=timezone.utc) if i.get("date") else None
    )]

    combined = all_new + existing
    combined.sort(key=lambda x: x.get("date", ""), reverse=True)
    combined = combined[:300]

    with open(FEED_PATH, "w") as f:
        json.dump(combined, f, indent=2)

    print(f"\nDone. {len(all_new)} new item(s) added. {len(combined)} total in feed.")


if __name__ == "__main__":
    main()
