"""
Ingest Srimad Bhagavatam (Bhagavata Purana) from GitHub ODT files.
Source: God-stories/Srimad-Bhagavatam (scraped from vedabase.com)
Translation: A.C. Bhaktivedanta Swami Prabhupada
All 12 Cantos, 335 chapters, ~18,000 verses.
Deterministic UUIDs → safe to re-run (upsert).
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
import sys
import uuid
import zipfile
from pathlib import Path

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.services.embeddings import embed_texts

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

RELIGION    = "Hinduism"
TRANSLATION = "Srimad Bhagavatam (tr. A.C. Bhaktivedanta Swami Prabhupada, vedabase.com)"
BATCH_SIZE  = 20
CONCURRENCY = 5

GITHUB_RAW = "https://raw.githubusercontent.com/God-stories/Srimad-Bhagavatam/master/raw%20files"
GITHUB_API = "https://api.github.com/repos/God-stories/Srimad-Bhagavatam/contents/raw%20files"

# (canto_num, chapters)
CANTO_CHAPTERS = {
    1: 19, 2: 10, 3: 33, 4: 31, 5: 26, 6: 19,
    7: 15, 8: 24, 9: 24, 10: 90, 11: 31, 12: 13,
}


def stable_id(canto: int, chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Hinduism:Bhagavatam:{canto}:{chapter}:{verse}"))


def parse_odt_verses(odt_bytes: bytes, canto: int, chapter: int) -> list[dict]:
    """
    Extract 'Text N: ...' verse entries from an ODT (zip+XML) file.
    Stops collecting a verse when the next 'Text N+1:' or 'PURPORT' is found.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(odt_bytes)) as z:
            with z.open("content.xml") as f:
                xml = f.read().decode("utf-8")
    except Exception:
        return []

    # Strip XML tags → plain text
    text = re.sub(r"<[^>]+>", " ", xml)
    text = re.sub(r"\s+", " ", text).strip()

    # Split on "Text N:" markers
    parts = re.split(r"\bText\s+(\d+)\s*:", text)
    # parts = [before_text_1, "1", body_of_1, "2", body_of_2, ...]

    verses = []
    for i in range(1, len(parts) - 1, 2):
        verse_num = int(parts[i])
        body = parts[i + 1].strip()

        # Remove purport section if present
        purport_idx = body.upper().find("PURPORT")
        if purport_idx != -1:
            body = body[:purport_idx].strip()

        # Clean up stray reference noise
        body = re.sub(r"\bText\s+\d+.*$", "", body, flags=re.DOTALL).strip()
        body = re.sub(r"\s+", " ", body).strip()

        if len(body) < 30:
            continue

        verses.append({
            "religion":    RELIGION,
            "text":        body,
            "translation": TRANSLATION,
            "book":        f"Bhagavata Purana – Canto {canto}",
            "chapter":     chapter,
            "verse":       verse_num,
            "reference":   f"SB {canto}.{chapter}.{verse_num}",
            "source_url":  f"https://vedabase.io/en/library/sb/{canto}/{chapter}/{verse_num}/",
        })

    return verses


def build_odt_url(canto: int, chapter: int) -> str:
    canto_dir = f"Canto%20{canto:02d}"
    filename  = f"Canto%20{canto}%20Chapter%20{chapter:02d}.odt"
    return f"{GITHUB_RAW}/{canto_dir}/{filename}"


async def fetch_chapter(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    canto: int,
    chapter: int,
) -> list[dict]:
    url = build_odt_url(canto, chapter)
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=30)
                if r.status_code == 404:
                    # Try without zero-padding on chapter
                    url2 = f"{GITHUB_RAW}/Canto%20{canto:02d}/Canto%20{canto}%20Chapter%20{chapter}.odt"
                    r2 = await client.get(url2, timeout=30)
                    if r2.status_code == 200:
                        return parse_odt_verses(r2.content, canto, chapter)
                    return []
                if r.status_code == 200:
                    verses = parse_odt_verses(r.content, canto, chapter)
                    return verses
            except Exception as exc:
                if attempt == 2:
                    logger.warning("Failed Canto %d Ch %d: %s", canto, chapter, exc)
                await asyncio.sleep(1 + attempt)
    return []


async def ingest_bhagavatam():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem = asyncio.Semaphore(CONCURRENCY)

    all_verses: list[dict] = []

    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0 CrossVerse/1.0"}) as http:
        for canto, max_ch in CANTO_CHAPTERS.items():
            logger.info("Fetching Canto %d (%d chapters)…", canto, max_ch)
            tasks = [fetch_chapter(http, sem, canto, ch) for ch in range(1, max_ch + 1)]
            results = await asyncio.gather(*tasks)
            canto_verses = [v for ch_vs in results for v in ch_vs]
            logger.info("  Canto %d: %d verses", canto, len(canto_verses))
            all_verses.extend(canto_verses)

    logger.info("Total Bhagavatam verses: %d", len(all_verses))

    if not all_verses:
        logger.error("No verses collected.")
        return

    total = 0
    for i in range(0, len(all_verses), BATCH_SIZE):
        batch = all_verses[i: i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(
                id=stable_id(v["chapter"] // 1000 + 1, v["chapter"], v["verse"]),
                vector=emb,
                payload=v,
            )
            for v, emb in zip(batch, embeddings)
        ]
        # Fix ID — use proper canto from book name
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS,
                    f"Hinduism:Bhagavatam:{v['book']}:{v['chapter']}:{v['verse']}")),
                vector=emb,
                payload=v,
            )
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)
        if total % 500 == 0 or total == len(all_verses):
            logger.info("Upserted %d / %d", total, len(all_verses))

    logger.info("Bhagavatam ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_bhagavatam())
