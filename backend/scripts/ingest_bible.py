"""
Ingest the King James Version Bible into Qdrant.

Data source: https://raw.githubusercontent.com/thiagobodruk/bible/master/json/en_kjv.json
Format: [{name, abbrev, chapters: [[verse_text, ...]]}]
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

# Allow running from the backend/ directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.services.embeddings import embed_texts

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

KJV_URL = "https://raw.githubusercontent.com/thiagobodruk/bible/master/json/en_kjv.json"
RELIGION = "Christianity"
TRANSLATION = "King James Version (KJV)"
BATCH_SIZE = 20


async def ingest_bible():
    settings = get_settings()
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    logger.info("Downloading KJV Bible from %s ...", KJV_URL)
    async with httpx.AsyncClient(timeout=120) as http:
        resp = await http.get(KJV_URL)
        resp.raise_for_status()
        books_data = resp.json()

    logger.info("Loaded %d books.", len(books_data))

    # Build flat list of verse dicts
    verses: list[dict] = []
    for book in books_data:
        book_name = book["name"]
        for chap_idx, chapter in enumerate(book["chapters"], start=1):
            for verse_idx, text in enumerate(chapter, start=1):
                text = text.strip()
                if not text:
                    continue
                reference = f"{book_name} {chap_idx}:{verse_idx}"
                verses.append(
                    {
                        "religion": RELIGION,
                        "text": text,
                        "translation": TRANSLATION,
                        "book": book_name,
                        "chapter": chap_idx,
                        "verse": verse_idx,
                        "reference": reference,
                        "source_url": KJV_URL,
                    }
                )

    logger.info("Total verses to ingest: %d", len(verses))

    # Process in batches
    total_upserted = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch = verses[i : i + BATCH_SIZE]
        texts = [v["text"] for v in batch]

        logger.info(
            "Embedding batch %d/%d (verses %d-%d)...",
            i // BATCH_SIZE + 1,
            (len(verses) + BATCH_SIZE - 1) // BATCH_SIZE,
            i + 1,
            i + len(batch),
        )
        embeddings = await embed_texts(texts, batch_size=BATCH_SIZE)

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=emb,
                payload=verse,
            )
            for verse, emb in zip(batch, embeddings)
        ]

        client.upsert(collection_name=settings.qdrant_collection, points=points)
        total_upserted += len(points)
        logger.info("Upserted %d / %d verses so far.", total_upserted, len(verses))

    logger.info("Bible ingestion complete. Total upserted: %d", total_upserted)


if __name__ == "__main__":
    asyncio.run(ingest_bible())
