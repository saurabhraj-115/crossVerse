"""
Ingest all 196 Yoga Sutras of Patanjali from the pd2/patanjali-yoga-sutra GitHub repo.
Uses the plain-text file which contains sutra numbers and English translations.
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

RELIGION    = "Hinduism"
TRANSLATION = "Yoga Sutras of Patanjali (Public Domain)"
BATCH_SIZE  = 20

# pd2 repo: tab-separated TSV with columns: pada, sutra, text
TSV_URL = (
    "https://raw.githubusercontent.com/pd2/patanjali-yoga-sutra/master/"
    "patanjali_yoga_sutra.txt"
)

PADA_NAMES = {
    1: "Samadhi Pada",
    2: "Sadhana Pada",
    3: "Vibhuti Pada",
    4: "Kaivalya Pada",
}


def stable_id(pada: int, sutra: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Hinduism:YogaSutras:{pada}:{sutra}"))


def parse_sutras(raw: str) -> list[dict]:
    """
    The file is JSON: a list of 4 padas, each a list of sutra objects:
    [
      [ {"shloka": "...", "meaning": "...", "words": "..."}, ... ],  # Pada 1
      [...],  # Pada 2
      [...],  # Pada 3
      [...],  # Pada 4
    ]
    """
    import json as _json
    try:
        data = _json.loads(raw)
    except Exception as e:
        logger.error("Failed to parse JSON: %s", e)
        return []

    verses = []
    for pada_idx, pada_sutras in enumerate(data, start=1):
        for sutra_idx, obj in enumerate(pada_sutras, start=1):
            meaning = (obj.get("meaning") or "").strip()
            shloka  = (obj.get("shloka") or "").strip()
            words   = (obj.get("words") or "").strip()
            if not meaning:
                continue
            # Build a rich text: meaning + words context
            text = meaning
            if words:
                text += f" ({words})"
            verses.append({
                "religion":    RELIGION,
                "text":        text,
                "translation": TRANSLATION,
                "book":        f"Yoga Sutras – {PADA_NAMES.get(pada_idx, f'Pada {pada_idx}')}",
                "chapter":     pada_idx,
                "verse":       sutra_idx,
                "reference":   f"YS {pada_idx}.{sutra_idx}",
                "source_url":  TSV_URL,
            })
    return verses


async def ingest_yoga_sutras_full():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    logger.info("Fetching Yoga Sutras from pd2/patanjali-yoga-sutra …")
    async with httpx.AsyncClient() as http:
        for attempt in range(3):
            try:
                r = await http.get(TSV_URL, timeout=20)
                if r.status_code == 200:
                    break
                logger.warning("HTTP %d on attempt %d", r.status_code, attempt + 1)
            except Exception as e:
                logger.warning("Attempt %d failed: %s", attempt + 1, e)
                await asyncio.sleep(2)
        else:
            logger.error("Could not fetch Yoga Sutras file — aborting.")
            return

    verses = parse_sutras(r.text)
    logger.info("Parsed %d Yoga Sutras", len(verses))

    if not verses:
        logger.error("No verses parsed — check the file format.")
        return

    total = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch = verses[i: i + BATCH_SIZE]
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
        logger.info("Upserted %d / %d", total, len(verses))

    logger.info("Yoga Sutras ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_yoga_sutras_full())
