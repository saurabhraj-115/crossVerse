"""
Ingest the Quran (English Sahih International translation) into Qdrant.

Data source: http://api.alquran.cloud/v1/quran/en.sahih
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

QURAN_API = "http://api.alquran.cloud/v1/quran/en.sahih"
RELIGION = "Islam"
TRANSLATION = "Sahih International"
BATCH_SIZE = 20


async def ingest_quran():
    settings = get_settings()
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    logger.info("Fetching Quran from alquran.cloud...")
    async with httpx.AsyncClient(timeout=120) as http:
        resp = await http.get(QURAN_API)
        resp.raise_for_status()
        data = resp.json()

    surahs = data["data"]["surahs"]
    logger.info("Loaded %d surahs.", len(surahs))

    verses: list[dict] = []
    for surah in surahs:
        surah_number = surah["number"]
        surah_name = surah["englishName"]
        for ayah in surah["ayahs"]:
            text = ayah["text"].strip()
            if not text:
                continue
            verse_number = ayah["numberInSurah"]
            reference = f"Quran {surah_number}:{verse_number}"
            verses.append(
                {
                    "religion": RELIGION,
                    "text": text,
                    "translation": TRANSLATION,
                    "book": f"Surah {surah_number}: {surah_name}",
                    "chapter": surah_number,
                    "verse": verse_number,
                    "reference": reference,
                    "source_url": QURAN_API,
                }
            )

    logger.info("Total ayahs to ingest: %d", len(verses))

    total_upserted = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch = verses[i : i + BATCH_SIZE]
        texts = [v["text"] for v in batch]

        logger.info(
            "Embedding batch %d/%d...",
            i // BATCH_SIZE + 1,
            (len(verses) + BATCH_SIZE - 1) // BATCH_SIZE,
        )
        embeddings = await embed_texts(texts, batch_size=BATCH_SIZE)

        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS,
                    f"Islam:Quran:{verse['chapter']}:{verse['verse']}")),
                vector=emb,
                payload=verse,
            )
            for verse, emb in zip(batch, embeddings)
        ]

        client.upsert(collection_name=settings.qdrant_collection, points=points)
        total_upserted += len(points)
        logger.info("Upserted %d / %d ayahs so far.", total_upserted, len(verses))

    logger.info("Quran ingestion complete. Total upserted: %d", total_upserted)


if __name__ == "__main__":
    asyncio.run(ingest_quran())
