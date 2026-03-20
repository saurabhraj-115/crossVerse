"""
Ingest three more Hadith collections from the fawazahmed0/hadith-api GitHub CDN:
  - Sunan al-Tirmidhi   (~3,900 hadiths)
  - Sunan Ibn Majah     (~4,300 hadiths)
  - Riyad as-Salihin   (~1,900 hadiths)

Same source CDN and parse pattern as ingest_hadith_extra.py.
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
        "name":        "Sunan al-Tirmidhi",
        "url":         "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/eng-tirmidhi.json",
        "id_prefix":   "Tirmidhi",
        "translation": "Sunan al-Tirmidhi (Public Domain)",
    },
    {
        "name":        "Sunan Ibn Majah",
        "url":         "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/eng-ibnmajah.json",
        "id_prefix":   "IbnMajah",
        "translation": "Sunan Ibn Majah (Public Domain)",
    },
    {
        "name":        "Riyad as-Salihin",
        "url":         "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/eng-riyadussalihin.json",
        "id_prefix":   "Riyad",
        "translation": "Riyad as-Salihin (Public Domain)",
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
        if not text or len(text.split()) < 8:
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


async def ingest_hadith_more():
    settings    = get_settings()
    client_q    = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
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

    logger.info("More Hadith ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_hadith_more())
