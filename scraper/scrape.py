"""
PulseFeed scraper — fetches planning commission RSS feeds, scrapes HTML source
pages for upcoming meetings, and parses linked PDFs for agenda item summaries.
Writes results to public/feed.json.

Run locally:  python scraper/scrape.py
"""

import argparse
import hashlib
import io
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse, unquote
from pathlib import Path
from source_workbook import WORKBOOK, REGISTRY, compile_registry, read_tables, atomic_json
from collection import (parse_date, link_date, document_link, planning_link, request_bytes,
                        begin_source, source_diagnostics, record_issue)

import feedparser
import pdfplumber
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Keyword filter
# ---------------------------------------------------------------------------

KEYWORDS = {
    "planning commission", "planning", "agenda", "minutes",
    "public hearing", "zoning", "variance", "site plan", "special use",
}

PDF_KEYWORDS = {"agenda", "minutes", "planning", "zoning", "variance"}


# ---------------------------------------------------------------------------
# Topic classification — zoning, housing, industrial
# ---------------------------------------------------------------------------

ZONING_KEYWORDS = {
    "zoning", "rezoning", "rezone", "variance", "ordinance", "conditional use",
    "special use", "site plan", "overlay", "setback", "land use", "master plan",
    "special land use", "text amendment", "zba", "zoning board", "zoning map",
    "zoning ordinance", "zoning amendment",
}
HOUSING_KEYWORDS = {
    "housing", "residential", "apartment", "dwelling", "affordable", "subdivision",
    "plat", "condominium", "condo", "single family", "multifamily", "multi-family",
    "duplex", "accessory dwelling", "adu", "short-term rental", "str", "townhouse",
    "senior housing", "mixed use",
}
INDUSTRIAL_KEYWORDS = {
    "industrial", "warehouse", "manufacturing", "logistics", "commercial",
    "business park", "distribution", "storage", "factory", "data center",
    "solar", "wind", "energy", "utility", "mining", "extraction", "gravel",
    "aggregate", "renewable",
}


def classify_topics(text: str) -> list[str]:
    t = text.lower()
    topics = []
    if any(kw in t for kw in ZONING_KEYWORDS):
        topics.append("Zoning")
    if any(kw in t for kw in HOUSING_KEYWORDS):
        topics.append("Housing")
    if any(kw in t for kw in INDUSTRIAL_KEYWORDS):
        topics.append("Industrial")
    return topics


def filter_pdf_by_topic(items_text: str) -> str:
    """Keep only agenda lines related to zoning, housing, or industrial topics."""
    if not items_text:
        return ""
    lines = items_text.splitlines()
    relevant = [l for l in lines if classify_topics(l)]
    return "\n".join(relevant) if relevant else ""


def extract_parcel_numbers(text: str) -> list[str]:
    """Extract unique Michigan-format parcel numbers from text."""
    found = PARCEL_RE.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for p in found:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


def detect_doc_type(url: str, title: str, pdf_text: str = "") -> str:
    """Return 'Minutes', 'Agenda', or '' based on URL, title, and PDF content."""
    combined = (url + " " + title).lower()
    preview = pdf_text[:800].lower()
    if "agenda" in combined or "packet" in combined:
        return "Agenda"
    if "minute" in combined:
        return "Minutes"
    if "agenda" in preview:
        return "Agenda"
    if "minute" in preview:
        return "Minutes"
    return ""

# ---------------------------------------------------------------------------
# HTTP config
# ---------------------------------------------------------------------------

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
AGENDA_ITEM_RE = re.compile(r'^\s*(\d+[\.\)]\s+|[A-Za-z][\.\)]\s+|[•\-\*]\s+)')
AGENDA_START_RE = re.compile(r'\bAGENDA\b', re.IGNORECASE)
AGENDA_END_RE = re.compile(r'\b(ADJOURNMENT|EXECUTIVE SESSION)\b', re.IGNORECASE)
WHITESPACE_RE = re.compile(r'\s+')
HTML_TAG_RE = re.compile(r'<[^>]+>')
# Michigan parcel numbers: ##-##-##-###-### (with optional 4th digit group)
PARCEL_RE = re.compile(r'\b\d{2}[-–]\d{2}[-–]\d{2}[-–]\d{3}[-–]\d{3,4}\b')

# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------

def is_relevant(title: str, summary: str) -> bool:
    combined = (title + " " + summary).lower()
    return any(kw in combined for kw in KEYWORDS)


def is_within_window(dt: datetime | None) -> bool:
    if dt is None:
        return True
    now = datetime.now(timezone.utc)
    year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    three_months_ago = now - timedelta(days=91)
    cutoff = max(year_start, three_months_ago)
    max_future = now + timedelta(days=365)
    return cutoff <= dt <= max_future


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
    return "Upcoming" if dt.date() >= datetime.now(timezone.utc).date() else "Recent"


def strip_html(text: str) -> str:
    return HTML_TAG_RE.sub(" ", text or "").strip()


def clean(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text or "").strip()


def parse_flexible_date(date_str: str) -> datetime | None:
    return parse_date(date_str)


def fetch_html(url: str) -> BeautifulSoup | None:
    raw, final_url = request_bytes(url)
    if raw is None:
        return None
    if b"sgcaptcha" in raw[:2000].lower() or b"awswaf" in raw[:2000].lower():
        record_issue(f"Site requires browser verification: {url}")
        return None
    soup = BeautifulSoup(raw, "lxml")
    soup._source_url = final_url
    return soup


def extract_pdf_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    seen: set[str] = set()
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        path = urlparse(href).path.lower()
        if document_link(href):
            full = urljoin(base_url, href)
            if full not in seen:
                seen.add(full)
                links.append(full)
    return links


def date_near_link(a_tag) -> str:
    date = link_date(a_tag)
    return date.strftime("%Y-%m-%d") if date else ""


def fetch_pdf_bytes(pdf_url: str) -> bytes | None:
    raw, _ = request_bytes(pdf_url, max_bytes=MAX_PDF_BYTES)
    if raw is not None and not raw.lstrip().startswith(b"%PDF-"):
        record_issue(f"Download is not a PDF: {pdf_url}")
        return None
    return raw


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


def _fetch_pdf_text(pdf_url: str) -> str:
    raw = fetch_pdf_bytes(pdf_url)
    if not raw:
        return ""
    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages[:6])
            if not text.strip():
                record_issue(f"PDF has no extractable text in the first six pages; OCR may be needed: {pdf_url}")
            return text
    except Exception as exc:
        record_issue(f"PDF parse error {pdf_url}: {exc}")
        return ""


def parse_pdf_agenda_items(pdf_url: str) -> str:
    return extract_agenda_items(_fetch_pdf_text(pdf_url))


def parse_pdf_full(pdf_url: str) -> dict:
    """Parse a PDF; return agenda items, parcel numbers, and detected doc type."""
    text = _fetch_pdf_text(pdf_url)
    if not text.strip():
        return {"items": "", "parcels": [], "doc_type": "", "status": "unavailable"}
    return {
        "status": "parsed",
        "items": extract_agenda_items(text),
        "parcels": extract_parcel_numbers(text),
        "doc_type": detect_doc_type(pdf_url, "", text),
    }


def is_pdf_relevant(pdf_url: str) -> bool:
    path = urlparse(pdf_url).path.lower()
    return any(kw in path for kw in PDF_KEYWORDS)

# ---------------------------------------------------------------------------
# RSS scraper
# ---------------------------------------------------------------------------

def scrape_rss(source: dict) -> list[dict]:
    if not source.get("rss"):
        return []
    items = []
    try:
        raw, _ = request_bytes(source["rss"])
        if raw is None:
            return []
        feed = feedparser.parse(raw)
        if not feed.get("version"):
            record_issue(f"Response is not an RSS/Atom feed: {source['rss']}")
            return []
        for entry in feed.entries[:20]:
            title = clean(entry.get("title", ""))
            summary = clean(strip_html(entry.get("summary", "") or entry.get("description", "")))

            if not re.search(r"planning[\s_-]*(?:commission|board)", title + " " + summary, re.I):
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
                "dateType": "publication",
                "time": "",
                "summary": summary[:400] if summary else "",
                "details": "",
                "link": link,
                "tag": classify_tag(dt),
                "docType": detect_doc_type(link, title),
                "topics": classify_topics(f"{title} {summary}"),
                "pdfItems": "",
                "parcels": [],
                "scrapedAt": datetime.now(timezone.utc).isoformat(),
            })

    except Exception as exc:
        record_issue(f"RSS parsing failed: {exc}")

    return items


def enrich_with_pdf(item: dict) -> dict:
    """Add pdfItems, parcels, and docType to an RSS item by parsing linked PDFs."""
    link = item.get("link", "")
    if not link:
        return item

    if document_link(link):
        result = parse_pdf_full(link)
        item["pdfStatus"] = result.get("status", "unchecked")
        pdf_items = filter_pdf_by_topic(result["items"])
        if pdf_items:
            item["pdfItems"] = pdf_items
            item["topics"] = sorted(set(item.get("topics", []) + classify_topics(pdf_items)))
        if result["parcels"]:
            item["parcels"] = result["parcels"]
        if result["doc_type"] and not item.get("docType"):
            item["docType"] = result["doc_type"]
        return item

    # Visit the linked HTML page and find attached PDFs
    soup = fetch_html(link)
    if not soup:
        return item

    pdf_links = extract_pdf_links(soup, link)
    ordered = sorted(pdf_links, key=lambda u: (0 if is_pdf_relevant(u) else 1))
    for pdf_url in ordered[:3]:
        result = parse_pdf_full(pdf_url)
        pdf_items = filter_pdf_by_topic(result["items"])
        if pdf_items:
            item["pdfItems"] = pdf_items
            item["topics"] = sorted(set(item.get("topics", []) + classify_topics(pdf_items)))
            if result["parcels"]:
                item["parcels"] = result["parcels"]
            if result["doc_type"] and not item.get("docType"):
                item["docType"] = result["doc_type"]
            break

    return item

# ---------------------------------------------------------------------------
# HTML source scraper — finds PDFs not surfaced by RSS
# ---------------------------------------------------------------------------

def scrape_html_source(source: dict, existing_ids: set[str]) -> list[dict]:
    """Collect dated PC downloads, including one-level document landing pages."""
    soup = fetch_html(source["url"])
    if soup is None:
        return []
    page_url = soup._source_url or source["url"]
    base = soup.find("base", href=True)
    base_url = urljoin(page_url, base["href"]) if base else page_url
    candidates = []
    visited = set()
    for anchor in soup.find_all("a", href=True):
        if anchor.find_parent(["nav", "header", "footer"]):
            continue
        if not planning_link(anchor, page_url):
            continue
        href = urljoin(base_url, anchor["href"])
        if urlparse(href).scheme not in {"http", "https"}:
            continue
        dt = link_date(anchor)
        if not dt:
            continue
        if not is_within_window(dt):
            continue
        title = clean(anchor.get_text(" ", strip=True))
        if document_link(href):
            candidates.append((href, dt, title))
        elif "/document/" in urlparse(href).path and href not in visited and len(visited) < 20:
            visited.add(href)
            child = fetch_html(href)
            if child is not None:
                child_base = child.find("base", href=True)
                child_url = child._source_url or href
                resolved_base = urljoin(child_url, child_base["href"]) if child_base else child_url
                for link in child.find_all("a", href=True):
                    if link.find_parent(["nav", "header", "footer"]):
                        continue
                    download = urljoin(resolved_base, link["href"])
                    # Only downloads in the document body; never global navigation PDFs.
                    if document_link(download) and ("download" in link.get_text().lower() or planning_link(link, href)):
                        candidates.append((download, dt, title))
    items = []
    for pdf_url, dt, title in candidates:
        item_id = make_id(source, pdf_url)
        if item_id in existing_ids:
            continue
        title = title or unquote(urlparse(pdf_url).path.rsplit("/", 1)[-1]) or "Planning Commission document"
        result = parse_pdf_full(pdf_url)
        pdf_items = filter_pdf_by_topic(result["items"])
        existing_ids.add(item_id)
        items.append({
            "id": item_id, "county": source["county"], "source": source["name"],
            "title": title, "date": dt.strftime("%Y-%m-%d"),
            "dateDisplay": format_display_date(dt), "time": "", "summary": pdf_items[:400],
            "details": "", "link": pdf_url, "tag": classify_tag(dt),
            "docType": detect_doc_type(pdf_url, title, result["items"]),
            "topics": classify_topics(f"{title} {pdf_items}"), "pdfItems": pdf_items,
            "parcels": result["parcels"], "pdfStatus": result.get("status", "unchecked"), "scrapedAt": datetime.now(timezone.utc).isoformat(),
        })
    return items


def date_from_url_slug(url: str) -> datetime | None:
    """Extract a date from a Joomla slug like 'agenda-june-2-2026' by replacing
    hyphens with spaces so DATE_RE can match the month name."""
    path_text = urlparse(url).path.replace('-', ' ').replace('/', ' ')
    m = DATE_RE.search(path_text)
    return parse_flexible_date(m.group(0)) if m else None


def scrape_joomla_docs(source: dict, existing_ids: set[str]) -> list[dict]:
    """Scrape Joomla K2 document pages that store download URLs in data-* attributes."""
    items: list[dict] = []

    for page_url in source["pages"]:
        soup = fetch_html(page_url)
        if not soup:
            continue

        seen_urls: set[str] = set()
        for tag in soup.find_all(True):
            for attr, val in tag.attrs.items():
                if not attr.startswith("data-"):
                    continue
                if not isinstance(val, str):
                    continue
                # Joomla /file download links
                if not (val.startswith("http") and val.rstrip("/").endswith("/file")):
                    continue
                if val in seen_urls or not is_pdf_relevant(val):
                    continue
                seen_urls.add(val)

                item_id = make_id(source, val)
                if item_id in existing_ids:
                    continue

                dt = date_from_url_slug(val)
                if not dt or not is_within_window(dt):
                    continue

                # Build title from the slug segment before /file
                slug = urlparse(val).path.rstrip("/").removesuffix("/file")
                slug = slug.rsplit("/", 1)[-1]        # last path segment
                slug = re.sub(r"^\d+-", "", slug)     # strip leading numeric ID
                title = slug.replace("-", " ").title()

                print(f"    Parsing PDF: {val}")
                result = parse_pdf_full(val)
                pdf_items = filter_pdf_by_topic(result["items"])
                topics = classify_topics(f"{title} {pdf_items}")
                doc_type = detect_doc_type(val, title, result["items"])
                time.sleep(0.5)

                existing_ids.add(item_id)
                items.append({
                    "id": item_id,
                    "county": source["county"],
                    "source": source["name"],
                    "title": title,
                    "date": dt.strftime("%Y-%m-%d"),
                    "dateDisplay": format_display_date(dt),
                    "time": "",
                    "summary": pdf_items[:400] if pdf_items else "",
                    "details": "",
                    "link": val,
                    "tag": classify_tag(dt),
                    "docType": doc_type,
                    "topics": topics,
                    "pdfItems": pdf_items,
                    "parcels": result["parcels"], "pdfStatus": result.get("status", "unchecked"),
                    "scrapedAt": datetime.now(timezone.utc).isoformat(),
                })

    return items

# ---------------------------------------------------------------------------
# CivicPlus AgendaCenter scraper (Georgetown Charter Township and similar)
# ---------------------------------------------------------------------------

CIVICPLUS_DATE_RE = re.compile(r'/_(\d{2})(\d{2})(\d{4})-')


def date_from_civicplus_link(href: str) -> datetime | None:
    """Extract date from CivicPlus link like /AgendaCenter/ViewFile/Agenda/_05202026-1681."""
    m = CIVICPLUS_DATE_RE.search(href)
    if not m:
        return None
    month, day, year = m.groups()
    try:
        return datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
    except ValueError:
        return None


def scrape_civicplus(source: dict, existing_ids: set[str]) -> list[dict]:
    """Scrape CivicPlus AgendaCenter pages for agenda and minutes PDFs."""
    soup = fetch_html(source["agenda_center_url"])
    if not soup:
        return []

    items: list[dict] = []
    seen_urls: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/AgendaCenter/ViewFile/" not in href:
            continue
        # Skip HTML-view and packet variants — the bare URL is the PDF
        if "html=true" in href or "packet=true" in href:
            continue
        if not is_pdf_relevant(href):
            continue

        full_url = urljoin(source["base_url"], href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        item_id = make_id(source, full_url)
        if item_id in existing_ids:
            continue

        dt = date_from_civicplus_link(href)
        if not dt or not is_within_window(dt):
            continue

        # Build title from surrounding row text
        parent = a.parent
        row_text = ""
        for _ in range(4):
            if parent is None:
                break
            row_text = parent.get_text(" ", strip=True)
            if len(row_text) > 15:
                break
            parent = parent.parent
        title = row_text[:120] if row_text else a.get_text(strip=True) or "Planning Commission Document"

        doc_type = "Minutes" if "/ViewFile/Minutes/" in href else "Agenda"

        print(f"    Parsing CivicPlus PDF: {full_url}")
        result = parse_pdf_full(full_url)
        pdf_items = filter_pdf_by_topic(result["items"])
        topics = classify_topics(f"{title} {pdf_items}")
        time.sleep(0.5)

        existing_ids.add(item_id)
        items.append({
            "id": item_id,
            "county": source["county"],
            "source": source["name"],
            "title": title,
            "date": dt.strftime("%Y-%m-%d"),
            "dateDisplay": format_display_date(dt),
            "time": "",
            "summary": pdf_items[:400] if pdf_items else "",
            "details": "",
            "link": full_url,
            "tag": classify_tag(dt),
            "docType": doc_type,
            "topics": topics,
            "pdfItems": pdf_items,
            "parcels": result["parcels"], "pdfStatus": result.get("status", "unchecked"),
            "scrapedAt": datetime.now(timezone.utc).isoformat(),
        })

    return items

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

FEED_PATH = os.path.join(os.path.dirname(__file__), "..", "public", "feed.json")


def load_existing(path=FEED_PATH) -> list[dict]:
    try:
        data = json.loads(Path(path).read_text())
    except FileNotFoundError:
        return []
    if not isinstance(data, list) or any(not isinstance(i, dict) or not all(k in i for k in ("id", "source", "county", "link")) for i in data):
        raise ValueError("Invalid existing feed; refusing to overwrite it")
    return data


def collect_source(source):
    runtime = {**source, **source["endpoints"]}
    handler = source["handler"]
    ids = set()
    if handler in {"rss_html", "candidate"}:
        items = []
        for item in scrape_rss(runtime):
            if item["id"] not in ids:
                ids.add(item["id"])
                items.append(enrich_with_pdf(item))
        items.extend(scrape_html_source(runtime, ids))
        return items
    if handler == "joomla":
        return scrape_joomla_docs(runtime, ids)
    if handler == "civicplus":
        return scrape_civicplus(runtime, ids)
    return []


def merge_feed(existing, collected, sources):
    # Replace records by stable legacy ID so re-uploaded documents can be refreshed.
    by_id = {}
    allowed = {(s["county"], s["name"]): s for s in sources if s["deploymentStatus"] == "Production"}
    for item in existing + collected:
        if item.get("manual") or (item["county"], item["source"]) not in allowed:
            continue
        date = parse_date(item.get("date", ""))
        if item.get("date") and date is None:
            continue
        if not is_within_window(date):
            continue
        previous = by_id.get(item["id"])
        if previous and item.get("pdfStatus") == "unavailable":
            item = dict(item)
            for field in ("pdfItems", "parcels", "summary", "topics"):
                if not item.get(field) and previous.get(field):
                    item[field] = previous[field]
            item["details"] = "PDF extraction failed on the latest check; previously extracted content is retained."
        by_id[item["id"]] = {**item, "tag": classify_tag(date),
                              "sourceId": allowed[(item["county"], item["source"])]["id"]}
    # Do not silently discard quieter municipalities with a global 300-item cap.
    return sorted(by_id.values(), key=lambda i: (i.get("date", ""), i["id"]), reverse=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(FEED_PATH).parent)
    parser.add_argument("--source", action="append", help="Source ID to inspect (repeatable; requires separate output directory)")
    parser.add_argument("--include-candidates", action="store_true", help="Trial pending sources; never activates them")
    parser.add_argument("--discovery-only", action="store_true", help="Skip PDF enrichment for an isolated collection audit")
    args = parser.parse_args()
    isolated = args.output_dir.resolve() != Path(FEED_PATH).parent.resolve()
    if (args.source or args.include_candidates or args.discovery_only) and not isolated:
        parser.error("Trial/partial runs require --output-dir outside public/ to protect the live feed")
    sources = compile_registry(read_tables(WORKBOOK))
    if not REGISTRY.exists() or json.loads(REGISTRY.read_text()) != sources:
        raise SystemExit("Registry differs from workbook: run python scraper/source_workbook.py --write")
    if args.source and set(args.source) - {s["id"] for s in sources}:
        parser.error("Unknown source ID")
    if args.discovery_only:
        global parse_pdf_full
        parse_pdf_full = lambda url: {"items": "", "parcels": [], "doc_type": ""}
    feed_path = args.output_dir / "feed.json"
    existing = load_existing(feed_path)
    collected, reports, trials = [], [], []
    for source in sources:
        if args.source and source["id"] not in args.source:
            continue
        begin_source()
        report = {"sourceId": source["id"], "name": source["name"],
                  "checkedAt": None, "itemsFound": 0, "status": "pending", "issues": []}
        pending = source["deploymentStatus"] != "Production"
        if source["handler"] == "manual":
            report["status"] = "manual"
        elif pending and not args.include_candidates:
            report["status"] = "pending"
        elif pending and source["deploymentStatus"] != "Ready for Testing":
            report["status"] = "manual" if source["deploymentStatus"] == "Manual Setup Needed" else "pending"
        else:
            print(f"Checking {source['id']}: {source['name']}", flush=True)
            report["checkedAt"] = datetime.now(timezone.utc).isoformat()
            try:
                items = collect_source(source)
            except Exception as exc:
                record_issue(f"Collector failed: {type(exc).__name__}: {exc}")
                items = []
            report.update(source_diagnostics())
            report["itemsFound"] = len(items)
            report["status"] = ("partial" if report["issues"] and items else
                                "error" if report["issues"] else
                                "collected" if items else "no_matches")
            for item in items:
                item["sourceId"] = source["id"]
            (trials if pending else collected).extend(items)
        reports.append(report)
    output = merge_feed(existing, collected, sources)
    atomic_json(feed_path, output)
    atomic_json(args.output_dir / "source-status.json", {
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "discoveryOnly": args.discovery_only, "sources": reports,
    })
    if args.include_candidates:
        atomic_json(args.output_dir / "candidate-feed.json", trials)
    print(f"{len(output)} feed items; {len(trials)} trial items; {len(reports)} source results.")


if __name__ == "__main__":
    main()
