"""
Ingest the complete Tanakh (Hebrew Bible, 39 books, ~23,145 verses) via the Sefaria API.
Uses the JPS 1917 / Sefaria English translation (public domain).
Generates deterministic IDs so re-running is safe (upsert = no duplicates).
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
TRANSLATION = "Tanakh (Sefaria / JPS 1917, Public Domain)"
BATCH_SIZE  = 20
CONCURRENCY = 8   # be polite to Sefaria

# Full Tanakh: (book_name, sections, chapters)
# Section used for metadata grouping
BOOKS = [
    # Torah
    ("Genesis",      "Torah",    50),
    ("Exodus",       "Torah",    40),
    ("Leviticus",    "Torah",    27),
    ("Numbers",      "Torah",    36),
    ("Deuteronomy",  "Torah",    34),
    # Nevi'im
    ("Joshua",       "Nevi'im",  24),
    ("Judges",       "Nevi'im",  21),
    ("I Samuel",     "Nevi'im",  31),
    ("II Samuel",    "Nevi'im",  24),
    ("I Kings",      "Nevi'im",  22),
    ("II Kings",     "Nevi'im",  25),
    ("Isaiah",       "Nevi'im",  66),
    ("Jeremiah",     "Nevi'im",  52),
    ("Ezekiel",      "Nevi'im",  48),
    ("Hosea",        "Nevi'im",  14),
    ("Joel",         "Nevi'im",   4),
    ("Amos",         "Nevi'im",   9),
    ("Obadiah",      "Nevi'im",   1),
    ("Jonah",        "Nevi'im",   4),
    ("Micah",        "Nevi'im",   7),
    ("Nahum",        "Nevi'im",   3),
    ("Habakkuk",     "Nevi'im",   3),
    ("Zephaniah",    "Nevi'im",   3),
    ("Haggai",       "Nevi'im",   2),
    ("Zechariah",    "Nevi'im",  14),
    ("Malachi",      "Nevi'im",   3),
    # Ketuvim
    ("Psalms",       "Ketuvim", 150),
    ("Proverbs",     "Ketuvim",  31),
    ("Job",          "Ketuvim",  42),
    ("Song of Songs","Ketuvim",   8),
    ("Ruth",         "Ketuvim",   4),
    ("Lamentations", "Ketuvim",   5),
    ("Ecclesiastes", "Ketuvim",  12),
    ("Esther",       "Ketuvim",  10),
    ("Daniel",       "Ketuvim",  12),
    ("Ezra",         "Ketuvim",  10),
    ("Nehemiah",     "Ketuvim",  13),
    ("I Chronicles", "Ketuvim",  29),
    ("II Chronicles","Ketuvim",  36),
]


def stable_id(book: str, chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Judaism:Tanakh:{book}:{chapter}:{verse}"))


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


async def fetch_chapter(client: httpx.AsyncClient, sem: asyncio.Semaphore,
                        book: str, section: str, chapter: int) -> list[dict]:
    book_encoded = book.replace(" ", "%20")
    url = f"https://www.sefaria.org/api/texts/{book_encoded}.{chapter}?lang=en&context=0&pad=0"
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    raw_verses = data.get("text", [])
                    if not raw_verses:
                        return []
                    verses = []
                    for i, verse_text in enumerate(raw_verses, start=1):
                        if isinstance(verse_text, list):
                            # Some books return nested lists (e.g. Psalms intro)
                            verse_text = " ".join(verse_text)
                        text = strip_html(str(verse_text)).strip()
                        if not text:
                            continue
                        verses.append({
                            "religion":    RELIGION,
                            "text":        text,
                            "translation": TRANSLATION,
                            "book":        f"{book} ({section})",
                            "chapter":     chapter,
                            "verse":       i,
                            "reference":   f"{book} {chapter}:{i}",
                            "source_url":  f"https://www.sefaria.org/{book_encoded}.{chapter}.{i}",
                        })
                    return verses
                elif r.status_code == 404:
                    return []
            except Exception as e:
                if attempt == 2:
                    logger.warning("Failed %s %d — %s", book, chapter, e)
                await asyncio.sleep(1)
    return []


async def ingest_tanakh_full():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem = asyncio.Semaphore(CONCURRENCY)

    # Build all chapter tasks
    tasks_meta = [(book, section, ch) for book, section, n_ch in BOOKS for ch in range(1, n_ch + 1)]
    logger.info("Fetching %d chapters across 39 Tanakh books from Sefaria …", len(tasks_meta))

    all_verses: list[dict] = []

    # Process in chunks of 50 chapters to avoid hammering Sefaria
    CHUNK = 50
    async with httpx.AsyncClient() as http:
        for start in range(0, len(tasks_meta), CHUNK):
            chunk = tasks_meta[start: start + CHUNK]
            results = await asyncio.gather(*[fetch_chapter(http, sem, b, s, c) for b, s, c in chunk])
            for verse_list in results:
                all_verses.extend(verse_list)
            logger.info("Fetched %d chapters so far → %d verses", start + len(chunk), len(all_verses))

    logger.info("Total Tanakh verses fetched: %d", len(all_verses))

    total = 0
    for i in range(0, len(all_verses), BATCH_SIZE):
        batch = all_verses[i: i + BATCH_SIZE]
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
        if total % 500 == 0 or total == len(all_verses):
            logger.info("Upserted %d / %d", total, len(all_verses))

    logger.info("Tanakh (full) ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_tanakh_full())
