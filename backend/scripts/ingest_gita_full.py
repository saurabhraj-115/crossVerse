"""
Ingest the complete Bhagavad Gita (all 700 verses) from vedicscriptures.github.io.
Uses Swami Sivananda's public-domain English translation.
Generates deterministic IDs so re-running is safe (upsert = no duplicates).
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.services.embeddings import embed_texts

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

RELIGION   = "Hinduism"
TRANSLATION = "Bhagavad Gita (Swami Sivananda, Public Domain)"
BATCH_SIZE  = 20
CONCURRENCY = 20   # simultaneous HTTP requests — GitHub Pages can handle it

# Verse counts per chapter
CHAPTER_VERSES = [47,72,43,42,29,47,30,28,34,42,55,20,35,27,20,24,28,78]

def stable_id(chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Hinduism:Gita:{chapter}:{verse}"))


async def fetch_verse(client: httpx.AsyncClient, sem: asyncio.Semaphore,
                      chapter: int, verse: int) -> dict | None:
    url = f"https://vedicscriptures.github.io/slok/{chapter}/{verse}/"
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    # Prefer Sivananda > Tej > Gambir translation
                    en = (data.get("siva", {}).get("et") or
                          data.get("tej",  {}).get("et") or
                          data.get("gambir",{}).get("et") or "")
                    if not en:
                        return None
                    return {
                        "religion":    RELIGION,
                        "text":        en.strip(),
                        "translation": TRANSLATION,
                        "book":        f"Bhagavad Gita Chapter {chapter}",
                        "chapter":     chapter,
                        "verse":       verse,
                        "reference":   f"Gita {chapter}:{verse}",
                        "source_url":  url,
                    }
            except Exception as e:
                if attempt == 2:
                    logger.warning("Failed %s:%s — %s", chapter, verse, e)
                await asyncio.sleep(1)
    return None


async def ingest_gita_full():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem = asyncio.Semaphore(CONCURRENCY)

    logger.info("Fetching all 700 Gita verses from vedicscriptures.github.io …")
    tasks = []
    async with httpx.AsyncClient() as http:
        for ch, count in enumerate(CHAPTER_VERSES, start=1):
            for v in range(1, count + 1):
                tasks.append(fetch_verse(http, sem, ch, v))
        results = await asyncio.gather(*tasks)

    verses = [r for r in results if r]
    logger.info("Fetched %d verses (skipped %d empty)", len(verses), len(tasks) - len(verses))

    total = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch = verses[i: i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(id=stable_id(v["chapter"], v["verse"]), vector=emb, payload=v)
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)
        logger.info("Upserted %d / %d", total, len(verses))

    logger.info("Bhagavad Gita (full) ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_gita_full())
