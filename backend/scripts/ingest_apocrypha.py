"""
Ingest the Christian Apocrypha / Deuterocanonical books (14 books, books 40-53)
from the KJVA (KJV with Apocrypha) JSON in the scrollmapper/bible_databases repo.

Source: https://github.com/scrollmapper/bible_databases (Public Domain)
Books ingested: I Esdras, II Esdras, Tobit, Judith, Additions to Esther, Wisdom,
                Sirach, Baruch, Prayer of Azariah, Susanna, Bel and the Dragon,
                Prayer of Manasses, I Maccabees, II Maccabees

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

RELIGION    = "Christianity"
TRANSLATION = "King James Version with Apocrypha (KJVA, Public Domain)"
BATCH_SIZE  = 20
MAX_WORDS   = 200

# KJVA JSON from scrollmapper — 80 books total; books 40-53 (0-indexed 39-52) are Apocrypha
KJVA_URL    = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/KJVA.json"
APOCRYPHA_BOOK_RANGE = range(39, 53)  # 0-indexed: books 40-53


def stable_id(book_name: str, chunk_idx: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Christianity:Apocrypha:{book_name}:{chunk_idx}"))


def clean_text(text: str) -> str:
    """Remove Strong's number tags like G1234 / H5678 if present, normalize whitespace."""
    text = re.sub(r"\b[GH]\d+\b", "", text)
    return re.sub(r"\s+", " ", text).strip()


def build_chunks(book_name: str, chapters: list[dict], max_words: int = MAX_WORDS) -> list[dict]:
    """
    Group consecutive verses into ~200-word chunks.
    Returns list of payload dicts ready for Qdrant.
    """
    chunks: list[dict] = []
    chunk_idx = 0
    buf_words: list[str] = []
    buf_parts: list[str] = []
    last_chapter = 1
    last_verse   = 1

    def flush():
        nonlocal chunk_idx
        if buf_parts:
            text = " ".join(buf_parts)
            if len(text.split()) >= 8:
                chunks.append({
                    "religion":    RELIGION,
                    "text":        text,
                    "translation": TRANSLATION,
                    "book":        book_name,
                    "chapter":     last_chapter,
                    "verse":       last_verse,
                    "reference":   f"{book_name} {last_chapter}:{last_verse}",
                    "source_url":  KJVA_URL,
                    "_chunk_idx":  chunk_idx,
                })
                chunk_idx += 1
            buf_words.clear()
            buf_parts.clear()

    for chapter in chapters:
        ch_num = chapter.get("chapter", 1)
        for v in chapter.get("verses", []):
            v_num = v.get("verse", 1)
            raw   = clean_text(v.get("text", ""))
            if not raw:
                continue
            words = raw.split()
            if len(buf_words) + len(words) > max_words and buf_words:
                flush()
            buf_words.extend(words)
            buf_parts.append(raw)
            last_chapter = ch_num
            last_verse   = v_num

    flush()
    return chunks


async def ingest_apocrypha():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    logger.info("Fetching KJVA JSON…")
    async with httpx.AsyncClient(
        headers={"User-Agent": "CrossVerse-Ingestion/1.0"},
        follow_redirects=True,
        timeout=120,
    ) as http:
        for attempt in range(3):
            try:
                r = await http.get(KJVA_URL)
                if r.status_code == 200:
                    data = r.json()
                    break
                logger.warning("Attempt %d: HTTP %d", attempt + 1, r.status_code)
            except Exception as e:
                logger.warning("Attempt %d failed: %s", attempt + 1, e)
            await asyncio.sleep(2 ** attempt)
        else:
            logger.error("Could not fetch KJVA JSON — aborting")
            return

    all_books = data.get("books", [])
    logger.info("KJVA: %d total books", len(all_books))

    grand_total = 0

    for i in APOCRYPHA_BOOK_RANGE:
        if i >= len(all_books):
            continue
        book = all_books[i]
        book_name = book.get("name", f"Book {i+1}")
        chapters  = book.get("chapters", [])

        chunks = build_chunks(book_name, chapters)
        if not chunks:
            logger.warning("No chunks for %s", book_name)
            continue

        logger.info("  %s: %d chunks", book_name, len(chunks))

        total = 0
        for j in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[j : j + BATCH_SIZE]
            for c in batch:
                c.pop("_chunk_idx", None)
            embeddings = await embed_texts([c["text"] for c in batch], batch_size=BATCH_SIZE)
            points = [
                PointStruct(
                    id=stable_id(book_name, k),
                    vector=emb,
                    payload=c,
                )
                for k, (c, emb) in enumerate(zip(batch, embeddings), start=j)
            ]
            client_q.upsert(collection_name=settings.qdrant_collection, points=points)
            total += len(points)

        grand_total += total
        logger.info("  %s: %d chunks ingested", book_name, total)

    logger.info("Apocrypha ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_apocrypha())
