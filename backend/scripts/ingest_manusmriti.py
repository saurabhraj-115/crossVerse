"""
Ingest Manusmriti (Laws of Manu) — G. Bühler translation (Public Domain).
Source: Archive.org — manusmriti-ed-1 (DjVuTXT)
  https://archive.org/download/manusmriti-ed-1/Manusmriti-Ed1_djvu.txt
12 chapters, ~2,685 verses.
Deterministic UUIDs → safe to re-run (upsert).
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

RELIGION    = "Hinduism"
TRANSLATION = "Manusmriti (Laws of Manu), tr. G. Bühler (SBE Vol 25, Public Domain)"
BOOK        = "Manusmriti (Laws of Manu)"
BATCH_SIZE  = 20

SOURCE_URL = "https://archive.org/download/manusmriti-ed-1/Manusmriti-Ed1_djvu.txt"

# Chapter names
CHAPTER_NAMES = {
    1:  "On the Creation",
    2:  "On Education and Studentship",
    3:  "On Marriage",
    4:  "On the Duties of Householders",
    5:  "On Purification",
    6:  "On Hermits and Ascetics",
    7:  "On Kings",
    8:  "On Judicature and Civil Law",
    9:  "On Inheritance, Women, and Mixed Classes",
    10: "On the Duties of Mixed Classes",
    11: "On Penance",
    12: "On Transmigration and Final Beatitude",
}

ROMAN_MAP = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
    "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12,
}

# Verse pattern: "1. text" or "1) text"
VERSE_RE = re.compile(r'^\s*(\d{1,4})[.\)]\s+(.+)', re.MULTILINE)
# Chapter header pattern
CHAPTER_RE = re.compile(r'CHAPTER\s+(I{1,3}|IV|V?I{0,3}|VI{1,3}|IX|XI{0,3}|XII)\.?', re.IGNORECASE)


def stable_id(chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS,
        f"Hinduism:Manusmriti:{chapter}:{verse}"))


def parse_djvu_text(text: str) -> list[dict]:
    """
    Parse the Archive.org DjVuTXT of the Bühler Manusmriti.
    Splits on CHAPTER headings, extracts numbered verses within each.
    """
    # Split into chapter sections
    parts = CHAPTER_RE.split(text)
    # parts = [preamble, roman_num, chapter_body, roman_num, chapter_body, ...]

    verses: list[dict] = []
    i = 1
    while i < len(parts) - 1:
        roman = parts[i].strip().upper()
        body  = parts[i + 1]
        i += 2

        chapter_num = ROMAN_MAP.get(roman)
        if not chapter_num:
            continue

        chapter_name = CHAPTER_NAMES.get(chapter_num, f"Chapter {chapter_num}")

        for m in VERSE_RE.finditer(body):
            verse_num  = int(m.group(1))
            verse_text = m.group(2).strip()
            verse_text = re.sub(r'\s+', ' ', verse_text)

            # Skip footnotes (short numeric lines) and obvious noise
            if len(verse_text) < 20:
                continue
            if re.match(r'^[\d\s,\.]+$', verse_text):
                continue
            # Skip page markers like "p. 12"
            if re.match(r'^p\.\s*\d+', verse_text):
                continue

            verses.append({
                "religion":    RELIGION,
                "text":        verse_text,
                "translation": TRANSLATION,
                "book":        BOOK,
                "chapter":     chapter_num,
                "verse":       verse_num,
                "reference":   f"Manusmriti {chapter_num}.{verse_num} — {chapter_name}",
                "source_url":  "https://archive.org/details/manusmriti-ed-1",
            })

        logger.info("  Chapter %d (%s): %d verses",
                    chapter_num, chapter_name,
                    sum(1 for v in verses if v["chapter"] == chapter_num))

    return verses


async def ingest_manusmriti():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    logger.info("Downloading Manusmriti from Archive.org …")

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 CrossVerse/1.0"},
        follow_redirects=True,
        timeout=120,
    ) as http:
        for attempt in range(3):
            try:
                r = await http.get(SOURCE_URL)
                if r.status_code == 200:
                    break
                logger.warning("HTTP %d on attempt %d", r.status_code, attempt + 1)
            except Exception as exc:
                if attempt == 2:
                    logger.error("Download failed: %s", exc)
                    return
                await asyncio.sleep(2 ** attempt)
        else:
            logger.error("All download attempts failed.")
            return

    logger.info("Downloaded %.1f KB — parsing …", len(r.content) / 1024)
    all_verses = parse_djvu_text(r.text)
    logger.info("Total Manusmriti verses: %d", len(all_verses))

    if not all_verses:
        logger.error("No verses parsed — check source format.")
        return

    total = 0
    for i in range(0, len(all_verses), BATCH_SIZE):
        batch = all_verses[i: i + BATCH_SIZE]
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
        if total % 300 == 0 or total == len(all_verses):
            logger.info("Upserted %d / %d", total, len(all_verses))

    logger.info("Manusmriti ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_manusmriti())
