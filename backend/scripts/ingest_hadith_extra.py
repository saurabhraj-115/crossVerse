"""
Ingest additional Hadith collections from the fawazahmed0/hadith-api GitHub CDN:
  - Sahih Muslim      (~7,000 hadiths)
  - Nawawi's 40 Hadith (42 hadiths)
  - Sunan Abu Dawud   (~4,500 hadiths)

Same source CDN and parse pattern as ingest_hadith_full.py (Bukhari).
Re-running is safe — deterministic UUIDs, upsert only.
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

RELIGION   = "Islam"
BATCH_SIZE = 20

COLLECTIONS = [
    {
        "name":       "Sahih Muslim",
        "url":        "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/eng-muslim.json",
        "id_prefix":  "Muslim",
        "translation": "Sahih Muslim (Abdul Hamid Siddiqui, Public Domain)",
    },
    {
        "name":       "Nawawi 40 Hadith",
        "url":        "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/eng-nawawi40.json",
        "id_prefix":  "Nawawi",
        "translation": "An-Nawawi's Forty Hadith (Ezzedin Ibrahim & Denys Johnson-Davies, Public Domain)",
    },
    {
        "name":       "Sunan Abu Dawud",
        "url":        "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/eng-abudawud.json",
        "id_prefix":  "AbuDawud",
        "translation": "Sunan Abu Dawud (Ahmad Hasan, Public Domain)",
    },
]


def stable_id(prefix: str, hadith_num: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Islam:Hadith:{prefix}:{hadith_num}"))


async def download_json(client: httpx.AsyncClient, url: str) -> dict | None:
    logger.info("Downloading %s …", url)
    for attempt in range(3):
        try:
            r = await client.get(url, timeout=180)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.warning("Attempt %d failed: %s", attempt + 1, e)
            await asyncio.sleep(5)
    return None


def parse_hadiths(data: dict, collection: dict) -> list[dict]:
    hadiths_raw = data.get("hadiths", [])
    verses = []
    for h in hadiths_raw:
        text = (h.get("text") or "").strip()
        if not text or len(text) < 20:
            continue
        num  = h.get("hadithnumber") or h.get("arabicnumber") or 0
        book = h.get("book") or 0
        verses.append({
            "religion":    RELIGION,
            "text":        text,
            "translation": collection["translation"],
            "book":        f"{collection['name']} – Book {book}",
            "chapter":     book if isinstance(book, int) else None,
            "verse":       num,
            "reference":   f"{collection['name']} {num}",
            "source_url":  collection["url"],
        })
    return verses


async def ingest_hadith_extra():
    settings  = get_settings()
    client_q  = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    grand_total = 0

    async with httpx.AsyncClient() as http:
        for col in COLLECTIONS:
            data = await download_json(http, col["url"])
            if not data:
                logger.error("Failed to download %s — skipping.", col["name"])
                continue

            verses = parse_hadiths(data, col)
            logger.info("Parsed %d hadiths from %s", len(verses), col["name"])

            total = 0
            for i in range(0, len(verses), BATCH_SIZE):
                batch      = verses[i : i + BATCH_SIZE]
                embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
                points = [
                    PointStruct(
                        id=stable_id(col["id_prefix"], v["verse"]),
                        vector=emb,
                        payload=v,
                    )
                    for v, emb in zip(batch, embeddings)
                ]
                client_q.upsert(collection_name=settings.qdrant_collection, points=points)
                total += len(points)
                if total % 500 == 0 or total == len(verses):
                    logger.info("  %s: upserted %d / %d", col["name"], total, len(verses))

            grand_total += total
            logger.info("Completed %s: %d hadiths", col["name"], total)

    logger.info("Extra Hadith ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_hadith_extra())
