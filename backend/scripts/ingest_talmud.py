"""
Ingest key tractates of the Babylonian Talmud via the Sefaria API.
Translation: William Davidson Talmud (Sefaria, CC BY-NC).

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
TRANSLATION = "Babylonian Talmud (William Davidson / Sefaria, CC BY-NC)"
BATCH_SIZE  = 20
CONCURRENCY = 5

# (tractate_name, max_chapters)
# max_chapters is a ceiling — fetch halts automatically on 404/empty.
TRACTATES = [
    ("Berakhot",    9),   # Blessings, prayer — most read tractate
    ("Shabbat",    24),   # Sabbath laws
    ("Sanhedrin",  11),   # Famous: "whoever saves one life saves the world"
    ("Bava Metzia", 10),  # Civil/business ethics
    ("Avoda Zara",  5),   # Relations with the world
    ("Makkot",      3),   # Punishment, famous ethical passages
    ("Horayot",     3),   # Legal rulings
]


def stable_id(tractate: str, chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Judaism:Talmud:{tractate}:{chapter}:{verse}"))


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


async def fetch_chapter(
    client: httpx.AsyncClient, sem: asyncio.Semaphore,
    tractate: str, chapter: int,
) -> list[dict]:
    encoded = tractate.replace(" ", "%20")
    url     = f"https://www.sefaria.org/api/texts/{encoded}.{chapter}?lang=en&context=0&pad=0"
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
                    for i, vt in enumerate(raw, start=1):
                        if isinstance(vt, list):
                            vt = " ".join(vt)
                        text = strip_html(str(vt)).strip()
                        if not text or len(text.split()) < 8:
                            continue
                        verses.append({
                            "religion":    RELIGION,
                            "text":        text,
                            "translation": TRANSLATION,
                            "book":        f"Talmud – {tractate}",
                            "chapter":     chapter,
                            "verse":       i,
                            "reference":   f"{tractate} {chapter}:{i}",
                            "source_url":  f"https://www.sefaria.org/{encoded}.{chapter}.{i}",
                        })
                    return verses
                if r.status_code == 404:
                    return []
            except Exception as e:
                if attempt == 2:
                    logger.warning("Failed %s ch.%d — %s", tractate, chapter, e)
                await asyncio.sleep(1)
    return []


async def ingest_tractate(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    tractate: str,
    max_chapters: int,
) -> list[dict]:
    all_verses: list[dict] = []
    for ch in range(1, max_chapters + 1):
        verses = await fetch_chapter(client, sem, tractate, ch)
        if not verses and ch > 1:
            break   # chapter not found — tractate finished
        all_verses.extend(verses)
    return all_verses


async def ingest_talmud():
    settings    = get_settings()
    client_q    = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem         = asyncio.Semaphore(CONCURRENCY)
    grand_total = 0

    async with httpx.AsyncClient() as http:
        for tractate, max_ch in TRACTATES:
            logger.info("Ingesting Talmud – %s…", tractate)
            all_verses = await ingest_tractate(http, sem, tractate, max_ch)

            if not all_verses:
                logger.warning("  No verses fetched for %s", tractate)
                continue

            total = 0
            for i in range(0, len(all_verses), BATCH_SIZE):
                batch      = all_verses[i : i + BATCH_SIZE]
                embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
                points = [
                    PointStruct(
                        id=stable_id(v["book"], v["chapter"], v["verse"]),
                        vector=emb,
                        payload=v,
                    )
                    for v, emb in zip(batch, embeddings)
                ]
                client_q.upsert(collection_name=settings.qdrant_collection, points=points)
                total += len(points)

            grand_total += total
            logger.info("  %s: %d passages ingested", tractate, total)

    logger.info("Talmud ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_talmud())
