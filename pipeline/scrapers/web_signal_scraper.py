"""
Web Signal Scraper — collects scam-related mentions from public sources.

Sources:
  - Google search results (via Custom Search JSON API)
  - Kaskus forum threads (via scraping)

Each hit is stored in `agent_signals` for the trust score pipeline to consume.
"""

import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime, timezone
import time
import logging
import os
import re

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SyumraBot/1.0; +https://syumra.id/bot)",
    "Accept-Language": "id-ID,id;q=0.9",
}

# Google Custom Search (optional — requires API key)
GOOGLE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY", "")
GOOGLE_CX = os.getenv("GOOGLE_CSE_CX", "")

SCAM_KEYWORDS = [
    "penipuan haji",
    "travel haji bodong",
    "korban umroh",
    "umroh gagal berangkat",
    "agen haji tipu",
]

KASKUS_SEARCH_URL = "https://www.kaskus.co.id/search?q={query}&forum_id=16"  # forum 16 = Travel


def fetch_page(url: str, retries: int = 3) -> str:
    """Fetch a page with retries and exponential backoff."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            log.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")


def google_search_signals(query: str) -> list[dict]:
    """Search Google Custom Search for scam-related signals."""
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        log.info("Google CSE not configured — skipping Google search")
        return []

    signals = []
    url = (
        f"https://www.googleapis.com/customsearch/v1"
        f"?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}"
        f"&q={requests.utils.quote(query)}&num=10&lr=lang_id"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        for item in data.get("items", []):
            signals.append({
                "source": "google_search",
                "text": f"{item.get('title', '')} — {item.get('snippet', '')}",
                "url": item.get("link", ""),
                "collected_at": datetime.now(timezone.utc),
            })
    except Exception as e:
        log.warning(f"Google CSE search failed: {e}")
    return signals


def kaskus_search_signals(query: str) -> list[dict]:
    """Scrape Kaskus search results for scam-related forum threads."""
    signals = []
    search_url = KASKUS_SEARCH_URL.format(query=requests.utils.quote(query))
    try:
        html = fetch_page(search_url)
        soup = BeautifulSoup(html, "lxml")
        threads = soup.select("div.thread-item, div.search-result-item")
        for thread in threads[:10]:  # cap at 10 per query
            title_el = thread.select_one("a.thread-title, h3 a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            snippet_el = thread.select_one("p, div.thread-content")
            snippet = snippet_el.get_text(strip=True)[:500] if snippet_el else ""
            signals.append({
                "source": "kaskus",
                "text": f"{title} — {snippet}",
                "url": title_el.get("href", ""),
                "collected_at": datetime.now(timezone.utc),
            })
    except Exception as e:
        log.warning(f"Kaskus search failed for '{query}': {e}")
    return signals


def match_agent_by_name(signal_text: str, conn) -> str | None:
    """
    Attempt to match a signal to a known agent by name substring.
    Returns agent_verification ID if found, None otherwise.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name FROM agent_verifications ORDER BY name"
        )
        agents = cur.fetchall()
    for agent_id, agent_name in agents:
        # Match if agent name (or significant part) appears in signal text
        name_parts = agent_name.lower().split()
        significant = [p for p in name_parts if len(p) > 3]
        if significant and all(p in signal_text.lower() for p in significant[:2]):
            return str(agent_id)
    return None


def store_signals(signals: list[dict], conn) -> int:
    """Store signals in agent_signals table. Returns count of stored signals."""
    stored = 0
    with conn.cursor() as cur:
        for s in signals:
            agent_id = match_agent_by_name(s["text"], conn)
            if not agent_id:
                # Store with NULL agent_verification_id for manual triage
                agent_id = None

            cur.execute(
                """
                INSERT INTO agent_signals
                    (id, agent_verification_id, source, text, collected_at, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), %(agent_id)s, %(source)s, %(text)s,
                     %(collected_at)s, NOW(), NOW())
                """,
                {
                    "agent_id": agent_id,
                    "source": s["source"],
                    "text": s["text"],
                    "collected_at": s["collected_at"],
                },
            )
            stored += 1
    conn.commit()
    return stored


def run(db_dsn: str) -> None:
    """Main entry point — scrape all sources for all keywords."""
    all_signals = []

    for keyword in SCAM_KEYWORDS:
        log.info(f"Scraping signals for: '{keyword}'")
        all_signals.extend(google_search_signals(keyword))
        time.sleep(1)  # be polite
        all_signals.extend(kaskus_search_signals(keyword))
        time.sleep(2)  # be polite

    log.info(f"Collected {len(all_signals)} raw signals")

    if not all_signals:
        log.info("No signals collected — nothing to store")
        return

    conn = psycopg2.connect(db_dsn)
    try:
        stored = store_signals(all_signals, conn)
        log.info(f"✅ Stored {stored} signals in agent_signals")
    finally:
        conn.close()


if __name__ == "__main__":
    run(os.environ["DATABASE_URL"])
