"""
PulseFeed scraper — fetches planning commission pages and extracts agenda/minutes links.
Writes results to public/feed.json, deduplicating against existing entries.

Run locally:  python scraper/scrape.py
GitHub Action runs this on a schedule and commits the result.
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Sources — mirrors src/sources.js
# ---------------------------------------------------------------------------

SOURCES = [
    # Allegan County
    {"county": "Allegan", "name": "Allegan Township Planning Commission", "url": "https://allegantownship.org/planning-commission/"},
    {"county": "Allegan", "name": "Casco Township Planning Commission", "url": "https://www.cascotownship.info/meetings---planning-commission.html"},
    {"county": "Allegan", "name": "Cheshire Township Planning Commission", "url": "https://cheshiretownshipmi.gov/minutes.html"},
    {"county": "Allegan", "name": "Clyde Township Planning Commission", "url": "https://clydetwp.com/"},
    {"county": "Allegan", "name": "Dorr Township Planning Commission", "url": "https://dorrtownshipmi.gov/-Minutes-Agendas/Planning-Commission"},
    {"county": "Allegan", "name": "Fillmore Township Planning Commission", "url": "https://fillmoretownship.org/board-minutes/"},
    {"county": "Allegan", "name": "Ganges Township Planning Commission", "url": "https://www.gangestownship.org/Planning-Commission-Meetings-Archive.html"},
    {"county": "Allegan", "name": "Gun Plain Township Planning Commission", "url": "https://www.gunplain.org/meeting-minutes-and-agendas/"},
    {"county": "Allegan", "name": "Heath Township Planning Commission", "url": "https://heathtownship.net/"},
    {"county": "Allegan", "name": "Hopkins Township Planning Commission", "url": "https://www.hopkinstownship.org/board-minutes/"},
    {"county": "Allegan", "name": "Laketown Township Planning Commission", "url": "https://laketowntwp.org/boards-commissions/"},
    {"county": "Allegan", "name": "Lee Township Planning Commission", "url": "http://www.leetwp.org/meetingminutes.htm"},
    {"county": "Allegan", "name": "Leighton Township Planning Commission", "url": "https://leightontownship.org/meetings-minutes/"},
    {"county": "Allegan", "name": "Manlius Township Planning Commission", "url": "https://www.manliustwp.org/boardmeetings"},
    {"county": "Allegan", "name": "Martin Township Planning Commission", "url": "https://www.martintownship.org/"},
    {"county": "Allegan", "name": "Monterey Township Planning Commission", "url": "https://www.montereytownship.org/"},
    {"county": "Allegan", "name": "Otsego Township Planning Commission", "url": "https://www.otsegotownship.org/building-planning-and-zoning/"},
    {"county": "Allegan", "name": "Overisel Township Planning Commission", "url": "https://overiseltownship.org/planning-commission/"},
    {"county": "Allegan", "name": "Salem Township Planning Commission", "url": "https://salemtownship.org/planning-commission"},
    {"county": "Allegan", "name": "Saugatuck Township Planning Commission", "url": "https://saugatucktownshipmi.gov/saugatuck-township-local-government/packets-agendas-minutes/agendas/"},
    {"county": "Allegan", "name": "Trowbridge Township Planning Commission", "url": "https://trowbridgetownship.org/"},
    {"county": "Allegan", "name": "Valley Township Planning Commission", "url": "https://valleytwp.org/minutes.htm"},
    {"county": "Allegan", "name": "Watson Township Planning Commission", "url": "https://watsontownshipmi.gov/"},
    {"county": "Allegan", "name": "Wayland Township Planning Commission", "url": "https://waytwp.org/departments/zoning/"},
    {"county": "Allegan", "name": "City of Allegan Planning Commission", "url": "https://www.cityofallegan.org/government/planning_commission.php"},

    # Ottawa County
    {"county": "Ottawa", "name": "Allendale Charter Township Planning Commission", "url": "https://allendalemi.gov/planning-commission/"},
    {"county": "Ottawa", "name": "Blendon Township Planning Commission", "url": "https://www.blendontownship-mi.gov/planning-commission/"},
    {"county": "Ottawa", "name": "Chester Township Planning Commission", "url": "https://www.chester-twp.org/documents/"},
    {"county": "Ottawa", "name": "Crockery Township Planning Commission", "url": "https://crockerytownship.gov/planning-commission/"},
    {"county": "Ottawa", "name": "Georgetown Charter Township Planning Commission", "url": "https://www.gtwp.com/155/Planning-Commission"},
    {"county": "Ottawa", "name": "Grand Haven Charter Township Planning Commission", "url": "https://ghtmi.gov/boards/planning-commission/"},
    {"county": "Ottawa", "name": "Holland Charter Township Planning Commission", "url": "https://www.hct.holland.mi.us/agendas-minutes/planning-commission"},
    {"county": "Ottawa", "name": "Jamestown Charter Township Planning Commission", "url": "https://twp.jamestown.mi.us/government/boards-and-minutes/planning-commission-agendas-minutes/"},
    {"county": "Ottawa", "name": "Olive Township Planning Commission", "url": "https://www.olivetownship.org/document-category/pcminutes/"},
    {"county": "Ottawa", "name": "Park Township Planning Commission", "url": "https://webgen1files1.revize.com/parktwpmi/Document_Center/Meeting%20Agenda_Minutes%20%26%20Packets/Planning%20Commission/"},
    {"county": "Ottawa", "name": "Polkton Charter Township Planning Commission", "url": "https://polktontownship.com/planning-commission/"},
    {"county": "Ottawa", "name": "Port Sheldon Township Planning Commission", "url": "https://www.portsheldontwp.org/planning-commission/"},
    {"county": "Ottawa", "name": "Robinson Township Planning Commission", "url": "https://robinsontwpmi.gov/"},
    {"county": "Ottawa", "name": "Spring Lake Township Planning Commission", "url": "https://springlaketwp.org/board/planning-commission/"},
    {"county": "Ottawa", "name": "Tallmadge Charter Township Planning Commission", "url": "https://tallmadge.com/minutes-agendas/"},
    {"county": "Ottawa", "name": "Wright Township Planning Commission", "url": "http://wrighttownshipottawami.gov/"},
    {"county": "Ottawa", "name": "Zeeland Charter Township Planning Commission", "url": "https://zeelandchartertwpmi.documents-on-demand.com/"},
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": "PulseFeed/1.0 (planning commission agenda monitor; contact@lakeshoreadvantage.com)"
}

AGENDA_KEYWORDS = {"agenda", "packet", "planning commission", "minutes", "meeting notice", "public hearing"}

DATE_PATTERNS = [
    re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4}\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
]

MONTH_ABBR = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def extract_date_str(text: str) -> str:
    for pattern in DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(0)
    return ""


def parse_date(date_str: str) -> datetime | None:
    """Try to parse a date string into a datetime for sorting."""
    if not date_str:
        return None
    for fmt in ("%B %d, %Y", "%B %d %Y", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def format_display_date(date_str: str) -> str:
    dt = parse_date(date_str)
    if dt:
        return dt.strftime("%a, %b %-d")
    return date_str


def classify_tag(date_str: str) -> str:
    dt = parse_date(date_str)
    if not dt:
        return "New"
    now = datetime.now()
    if dt.date() >= now.date():
        return "Upcoming"
    return "Recent"


def make_id(source: dict, url: str) -> str:
    key = f"{source['county']}-{source['name']}-{url}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def abs_url(href: str, base: str) -> str:
    if href.startswith("http"):
        return href
    return urljoin(base, href)


def is_relevant_link(text: str, href: str) -> bool:
    combined = (text + " " + href).lower()
    return any(kw in combined for kw in AGENDA_KEYWORDS)


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

def scrape_source(source: dict) -> list[dict]:
    items = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        seen_urls: set[str] = set()

        for tag in soup.find_all("a", href=True):
            text = tag.get_text(" ", strip=True)
            href = tag["href"]

            if not is_relevant_link(text, href):
                continue
            if len(text) < 4:
                continue

            link = abs_url(href, source["url"])
            if link in seen_urls:
                continue
            seen_urls.add(link)

            # Look for a date in the link text or surrounding context
            context = text
            parent = tag.parent
            if parent:
                context += " " + parent.get_text(" ", strip=True)
            date_str = extract_date_str(context)

            items.append({
                "id": make_id(source, link),
                "county": source["county"],
                "source": source["name"],
                "title": text if len(text) > 10 else f"{source['name']} — agenda posted",
                "date": date_str,
                "dateDisplay": format_display_date(date_str),
                "time": "",
                "summary": f"New posting detected at {source['name']}.",
                "details": "",
                "link": link,
                "tag": classify_tag(date_str),
                "scrapedAt": datetime.now(timezone.utc).isoformat(),
            })

    except Exception as exc:
        print(f"  ERROR {source['name']}: {exc}")

    # Return the 5 most-recent-looking items (prefer ones with dates)
    items.sort(key=lambda x: parse_date(x["date"]) or datetime.min, reverse=True)
    return items[:5]


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
    for source in SOURCES:
        print(f"  Scraping {source['name']}...")
        new_items = [i for i in scrape_source(source) if i["id"] not in existing_ids]
        all_new.extend(new_items)
        time.sleep(0.75)  # polite crawl rate

    combined = all_new + existing
    # Sort: items with dates first (most recent), then undated
    combined.sort(
        key=lambda x: parse_date(x.get("date", "")) or datetime.min,
        reverse=True,
    )
    combined = combined[:300]  # cap at 300 items

    with open(FEED_PATH, "w") as f:
        json.dump(combined, f, indent=2)

    print(f"\nDone. {len(all_new)} new item(s) added. {len(combined)} total in feed.")


if __name__ == "__main__":
    main()
