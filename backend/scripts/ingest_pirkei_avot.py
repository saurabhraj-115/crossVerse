"""
Ingest Pirkei Avot (Ethics of the Fathers) — 6 chapters, ~185 mishnayot.
Source: Sefaria API (same pattern as ingest_tanakh_full.py).
Translation: Sefaria community / Bartenura (CC BY-SA).
Re-running is safe — deterministic UUIDs, upsert only.
"""

from __future__ import annotations

import asyncio
import logging
import re
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

RELIGION    = "Judaism"
TRANSLATION = "Pirkei Avot (Sefaria / William Davidson, CC BY-SA)"
BATCH_SIZE  = 20
NUM_CHAPTERS = 6   # Pirkei Avot has 6 chapters


def stable_id(chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Judaism:PirkeiAvot:{chapter}:{verse}"))


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


async def fetch_chapter(client: httpx.AsyncClient, sem: asyncio.Semaphore, chapter: int) -> list[dict]:
    url = f"https://www.sefaria.org/api/texts/Pirkei_Avot.{chapter}?lang=en&context=0&pad=0"
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    raw  = data.get("text", [])
                    if not raw:
                        return []
                    verses = []
                    for i, verse_text in enumerate(raw, start=1):
                        if isinstance(verse_text, list):
                            verse_text = " ".join(verse_text)
                        text = strip_html(str(verse_text)).strip()
                        if not text:
                            continue
                        verses.append({
                            "religion":    RELIGION,
                            "text":        text,
                            "translation": TRANSLATION,
                            "book":        "Pirkei Avot (Mishnah)",
                            "chapter":     chapter,
                            "verse":       i,
                            "reference":   f"Avot {chapter}:{i}",
                            "source_url":  f"https://www.sefaria.org/Pirkei_Avot.{chapter}.{i}",
                        })
                    return verses
                if r.status_code == 404:
                    return []
            except Exception as e:
                if attempt == 2:
                    logger.warning("Failed Pirkei Avot ch.%d — %s", chapter, e)
                await asyncio.sleep(1)
    return []


async def ingest_pirkei_avot():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem = asyncio.Semaphore(5)

    all_verses: list[dict] = []
    async with httpx.AsyncClient() as http:
        tasks   = [fetch_chapter(http, sem, ch) for ch in range(1, NUM_CHAPTERS + 1)]
        results = await asyncio.gather(*tasks)
        for verse_list in results:
            all_verses.extend(verse_list)

    logger.info("Fetched %d Pirkei Avot mishnayot", len(all_verses))

    total = 0
    for i in range(0, len(all_verses), BATCH_SIZE):
        batch      = all_verses[i : i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(
                id=stable_id(v["chapter"], v["verse"]),
                vector=emb,
                payload=v,
            )
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)

    logger.info("Pirkei Avot ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_pirkei_avot())
