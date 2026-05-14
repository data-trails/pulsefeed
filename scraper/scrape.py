"""
PulseFeed scraper — fetches planning commission RSS feeds and filters for
agenda/minutes posts. Writes results to public/feed.json.

Run locally:  python scraper/scrape.py
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone

import feedparser

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
# Keyword filter — only keep posts relevant to planning commission activity
# ---------------------------------------------------------------------------

KEYWORDS = {
    "planning commission", "planning", "agenda", "minutes",
    "public hearing", "zoning", "variance", "site plan", "special use",
}

def is_relevant(title: str, summary: str) -> bool:
    combined = (title + " " + summary).lower()
    return any(kw in combined for kw in KEYWORDS)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    import re
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def clean(text: str) -> str:
    import re
    return re.sub(r"\s+", " ", text or "").strip()

# ---------------------------------------------------------------------------
# Scraper
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

            # Parse published date
            published_tuple = entry.get("published_parsed") or entry.get("updated_parsed")
            dt = datetime(*published_tuple[:6], tzinfo=timezone.utc) if published_tuple else None

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
        print(f"  Fetching {source['name']}...")
        new_items = [i for i in scrape_rss(source) if i["id"] not in existing_ids]
        print(f"    {len(new_items)} new item(s)")
        all_new.extend(new_items)
        time.sleep(0.5)

    combined = all_new + existing
    combined.sort(key=lambda x: x.get("date", ""), reverse=True)
    combined = combined[:300]

    with open(FEED_PATH, "w") as f:
        json.dump(combined, f, indent=2)

    print(f"\nDone. {len(all_new)} new item(s) added. {len(combined)} total in feed.")


if __name__ == "__main__":
    main()
