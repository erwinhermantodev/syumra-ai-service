import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime, timezone
import time
import logging
import os

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

KEMENAG_URL = "https://haji.kemenag.go.id/v4/node/regulasi"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SyumraBot/1.0; +https://syumra.id/bot)",
    "Accept-Language": "id-ID,id;q=0.9",
}


def fetch_page(url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            log.warning(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")


def parse_agents(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    agents = []
    table = soup.select_one("table.views-table")
    if not table:
        log.warning("Agent table not found — page structure may have changed")
        return agents
    for row in table.select("tbody tr"):
        cols = row.select("td")
        if len(cols) < 5:
            continue
        agents.append({
            "license_number": cols[0].get_text(strip=True),
            "name": cols[1].get_text(strip=True),
            "city": cols[2].get_text(strip=True),
            "province": cols[3].get_text(strip=True),
            "valid_until": cols[4].get_text(strip=True),
            "scraped_at": datetime.now(timezone.utc),
            "ppiu_verified": True,
            "source": "kemenag",
        })
    return agents


def upsert_agents(agents: list[dict], conn) -> None:
    with conn.cursor() as cur:
        for a in agents:
            cur.execute(
                """
                INSERT INTO agent_verifications
                    (license_number, name, city, province, valid_until, scraped_at, ppiu_verified, source)
                VALUES
                    (%(license_number)s, %(name)s, %(city)s, %(province)s,
                     %(valid_until)s, %(scraped_at)s, %(ppiu_verified)s, %(source)s)
                ON CONFLICT (license_number) DO UPDATE SET
                    name          = EXCLUDED.name,
                    city          = EXCLUDED.city,
                    province      = EXCLUDED.province,
                    valid_until   = EXCLUDED.valid_until,
                    scraped_at    = EXCLUDED.scraped_at,
                    ppiu_verified = true
                """,
                a,
            )
    conn.commit()
    log.info(f"Upserted {len(agents)} agents")


def run(db_dsn: str) -> None:
    html = fetch_page(KEMENAG_URL)
    agents = parse_agents(html)
    # Safety check: abort if too few agents parsed (page structure change)
    if len(agents) < 100:
        log.error(
            f"Safety check failed: only {len(agents)} agents parsed "
            f"(expected ≥100). Aborting DB write."
        )
        return
    conn = psycopg2.connect(db_dsn)
    try:
        upsert_agents(agents, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    run(os.environ["DATABASE_URL"])
