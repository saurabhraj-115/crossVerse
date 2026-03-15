"""
Ingest the complete Guru Granth Sahib (1430 angs/pages) via the BaniDB public API.
Uses the BaniDB English translation (translation.en.bdb).
Generates deterministic IDs so re-running is safe (upsert = no duplicates).

API: https://api.banidb.com/v2/angs/{ang}/G
Each ang (page) returns a list of lines; we skip headers/raags and keep shabads.
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

RELIGION    = "Sikhism"
TRANSLATION = "Guru Granth Sahib (BaniDB English Translation)"
BATCH_SIZE  = 20
CONCURRENCY = 15   # be polite to the public API

TOTAL_ANGS  = 1430
BASE_URL    = "https://api.banidb.com/v2/angs/{ang}/G"


def stable_id(ang: int, line_id: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Sikhism:GGS:{ang}:{line_id}"))


def extract_lines(ang: int, data: dict) -> list[dict]:
    """Extract verses with English translation from an ang's JSON payload."""
    verses = []
    lines = data.get("page", [])
    for line in lines:
        # Skip lines without meaningful English text
        en_obj = (line.get("translation") or {}).get("en") or {}
        en_text = (
            (en_obj.get("bdb") or "").strip()
            or (en_obj.get("ms") or "").strip()
            or (en_obj.get("ssk") or "").strip()
        )
        if not en_text or len(en_text) < 10:
            continue

        line_id   = line.get("lineNo") or line.get("verseId") or 0
        shabad_id = line.get("shabadId") or 0
        verse_no  = line.get("verseno") or line.get("lineNo") or 0
        writer    = (line.get("writer") or {}).get("en", "")
        section   = (line.get("raag") or {}).get("en", "") or (line.get("source") or {}).get("en", "")

        book_label = f"Sri Guru Granth Sahib Ji"
        if section:
            book_label = f"SGGS – {section}"

        verses.append({
            "religion":    RELIGION,
            "text":        en_text,
            "translation": TRANSLATION,
            "book":        book_label,
            "chapter":     ang,         # ang = page number
            "verse":       verse_no,
            "reference":   f"SGGS Ang {ang}, Line {line_id}",
            "source_url":  BASE_URL.format(ang=ang),
            "_line_id":    line_id,
        })
    return verses


async def fetch_ang(client: httpx.AsyncClient, sem: asyncio.Semaphore,
                    ang: int) -> list[dict]:
    url = BASE_URL.format(ang=ang)
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=20)
                if r.status_code == 200:
                    return extract_lines(ang, r.json())
                elif r.status_code == 404:
                    return []
            except Exception as e:
                if attempt == 2:
                    logger.warning("Failed ang %d — %s", ang, e)
                await asyncio.sleep(1)
    return []


async def ingest_guru_granth_full():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem = asyncio.Semaphore(CONCURRENCY)

    logger.info("Fetching GGS angs 1–%d from BaniDB API …", TOTAL_ANGS)

    all_verses: list[dict] = []

    # Process in chunks of 100 angs to avoid holding 1430 HTTP connections open
    CHUNK = 100
    async with httpx.AsyncClient() as http:
        for start in range(1, TOTAL_ANGS + 1, CHUNK):
            end = min(start + CHUNK - 1, TOTAL_ANGS)
            tasks = [fetch_ang(http, sem, ang) for ang in range(start, end + 1)]
            results = await asyncio.gather(*tasks)
            chunk_verses = [v for ang_verses in results for v in ang_verses]
            all_verses.extend(chunk_verses)
            logger.info("Fetched angs %d–%d → %d lines so far", start, end, len(all_verses))

    logger.info("Total GGS lines with English translation: %d", len(all_verses))

    total = 0
    for i in range(0, len(all_verses), BATCH_SIZE):
        batch = all_verses[i: i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(
                id=stable_id(v["chapter"], v["_line_id"]),
                vector=emb,
                payload={k: val for k, val in v.items() if k != "_line_id"},
            )
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)
        if total % 500 == 0 or total == len(all_verses):
            logger.info("Upserted %d / %d", total, len(all_verses))

    logger.info("Guru Granth Sahib (full) ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_guru_granth_full())
