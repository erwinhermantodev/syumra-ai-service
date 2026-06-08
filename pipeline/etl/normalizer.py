"""
ETL Normalizer — post-processes raw agent signals collected by scrapers.

Pipeline steps:
  1. Fetch unprocessed signals from `agent_signals`
  2. Deduplicate near-identical text
  3. Run basic sentiment analysis (keyword-based, upgradable to ML)
  4. Mark signals as processed with sentiment score

Runs as a cron job after scraper passes.
"""

import psycopg2
from datetime import datetime, timezone
import logging
import os
import re
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Keyword-based sentiment scoring (simple baseline)
# Negative keywords → push sentiment toward 0 (bad)
# Positive keywords → push sentiment toward 1 (good)
NEGATIVE_KEYWORDS = [
    "tipu", "penipuan", "bodong", "korban", "gagal", "rugi", "bohong",
    "palsu", "tidak berangkat", "kabur", "hilang", "ditahan", "marah",
    "kecewa", "laporkan", "polisi", "tertipu", "scam", "fraud",
    "illegal", "unlicensed", "fake",
]

POSITIVE_KEYWORDS = [
    "terpercaya", "resmi", "aman", "puas", "recommended", "bagus",
    "mantap", "legal", "izin", "terverifikasi", "alhamdulillah",
    "lancar", "sukses", "trusted", "licensed", "verified",
]


def compute_sentiment(text: str) -> float:
    """
    Simple keyword-based sentiment score in range [0.0, 1.0].
    0.0 = very negative, 0.5 = neutral, 1.0 = very positive.
    """
    text_lower = text.lower()
    neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    total = neg_count + pos_count
    if total == 0:
        return 0.5  # neutral
    # Scale: 0 = all negative, 1 = all positive
    return round(pos_count / total, 3)


def text_similarity(a: str, b: str) -> float:
    """Compute text similarity ratio between two strings."""
    return SequenceMatcher(None, a[:200].lower(), b[:200].lower()).ratio()


def fetch_unprocessed(conn) -> list[dict]:
    """Fetch signals that haven't been processed yet."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, agent_verification_id, source, text, collected_at
            FROM agent_signals
            WHERE processed_at IS NULL
            ORDER BY collected_at
            LIMIT 500
            """
        )
        rows = cur.fetchall()
    return [
        {
            "id": str(row[0]),
            "agent_verification_id": str(row[1]) if row[1] else None,
            "source": row[2],
            "text": row[3] or "",
            "collected_at": row[4],
        }
        for row in rows
    ]


def deduplicate(signals: list[dict], threshold: float = 0.85) -> list[dict]:
    """
    Remove near-duplicate signals based on text similarity.
    Keeps the first occurrence of similar texts.
    """
    unique = []
    for signal in signals:
        is_dup = False
        for existing in unique:
            if text_similarity(signal["text"], existing["text"]) > threshold:
                is_dup = True
                log.debug(f"Dedup: '{signal['text'][:60]}...' matches existing")
                break
        if not is_dup:
            unique.append(signal)
    return unique


def process_and_update(signals: list[dict], conn) -> int:
    """
    Compute sentiment for each signal and update the DB.
    Returns count of updated signals.
    """
    updated = 0
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        for s in signals:
            sentiment = compute_sentiment(s["text"])
            cur.execute(
                """
                UPDATE agent_signals
                SET sentiment_score = %s,
                    processed_at = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (sentiment, now, now, s["id"]),
            )
            updated += 1
    conn.commit()
    return updated


def mark_duplicates_processed(all_signals: list[dict], unique_signals: list[dict], conn) -> int:
    """Mark duplicate signals as processed with NULL sentiment (excluded)."""
    unique_ids = {s["id"] for s in unique_signals}
    dup_ids = [s["id"] for s in all_signals if s["id"] not in unique_ids]
    if not dup_ids:
        return 0
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        for dup_id in dup_ids:
            cur.execute(
                """
                UPDATE agent_signals
                SET processed_at = %s, updated_at = %s
                WHERE id = %s
                """,
                (now, now, dup_id),
            )
    conn.commit()
    return len(dup_ids)


def run(db_dsn: str) -> None:
    """Main ETL pipeline entry point."""
    conn = psycopg2.connect(db_dsn)
    try:
        raw = fetch_unprocessed(conn)
        log.info(f"Fetched {len(raw)} unprocessed signals")

        if not raw:
            log.info("Nothing to process")
            return

        unique = deduplicate(raw)
        dup_count = len(raw) - len(unique)
        log.info(f"Deduplicated: {dup_count} duplicates removed, {len(unique)} unique signals")

        # Process unique signals with sentiment
        updated = process_and_update(unique, conn)
        log.info(f"✅ Sentiment computed for {updated} signals")

        # Mark duplicates as processed (no sentiment)
        if dup_count > 0:
            marked = mark_duplicates_processed(raw, unique, conn)
            log.info(f"🗑️  Marked {marked} duplicates as processed")

    finally:
        conn.close()


if __name__ == "__main__":
    run(os.environ["DATABASE_URL"])
