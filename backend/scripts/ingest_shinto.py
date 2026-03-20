"""
Ingest Shinto scriptures from Project Gutenberg (Public Domain):
  - Kojiki (Records of Ancient Matters)  — Basil Hall Chamberlain (PG #4029)
  - Nihongi (Chronicles of Japan)        — W.G. Aston (PG #45235)

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

RELIGION   = "Shinto"
BATCH_SIZE = 20
MAX_WORDS  = 200

TEXTS = [
    {
        "url":         "https://www.gutenberg.org/cache/epub/4029/pg4029.txt",
        "name":        "Kojiki (Records of Ancient Matters)",
        "id_prefix":   "Kojiki",
        "translation": "Kojiki (Basil Hall Chamberlain, Public Domain)",
        "book":        "Kojiki",
    },
    {
        "url":         "https://www.gutenberg.org/cache/epub/45235/pg45235.txt",
        "name":        "Nihongi (Chronicles of Japan)",
        "id_prefix":   "Nihongi",
        "translation": "Nihongi (W.G. Aston, Public Domain)",
        "book":        "Nihongi – Chronicles of Japan",
    },
]

_SKIP_KWS = {
    "gutenberg", "project gutenberg", "transcriber", "footnote",
    "produced by", "www.gutenberg", "ebook", "online distributed",
    "public domain", "unicode", "utf-8",
}


def clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_gutenberg_body(raw: str) -> str:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    start = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG", raw, re.IGNORECASE)
    end   = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG", raw, re.IGNORECASE)
    if start and end:
        return raw[start.end():end.start()]
    return raw


def parse_into_chunks(body: str, max_words: int = MAX_WORDS) -> list[tuple[int, str]]:
    """
    Split body text into 200-word chunks.
    Returns list of (chunk_idx, text).
    """
    lines = body.splitlines()
    chunks: list[tuple[int, str]] = []
    chunk_idx    = 0
    buf_words: list[str] = []
    buf_parts: list[str] = []

    def flush():
        nonlocal chunk_idx
        if buf_parts:
            text = clean_ws(" ".join(buf_parts))
            if len(text.split()) >= 8:
                chunks.append((chunk_idx, text))
                chunk_idx += 1
            buf_words.clear()
            buf_parts.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(kw in stripped.lower() for kw in _SKIP_KWS):
            continue

        words = stripped.split()
        if len(buf_words) + len(words) > max_words and buf_words:
            flush()

        buf_words.extend(words)
        buf_parts.append(stripped)

    flush()
    return chunks


async def fetch_text(client: httpx.AsyncClient, url: str) -> str:
    for attempt in range(3):
        try:
            r = await client.get(url, timeout=60)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                logger.warning("404 for %s", url)
                return ""
        except Exception as e:
            if attempt == 2:
                logger.warning("Failed %s — %s", url, e)
            await asyncio.sleep(2 ** attempt)
    return ""


async def ingest_shinto():
    settings    = get_settings()
    client_q    = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    grand_total = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": "CrossVerse-Ingestion/1.0"},
        follow_redirects=True,
    ) as http:
        for cfg in TEXTS:
            logger.info("Fetching %s…", cfg["name"])
            raw = await fetch_text(http, cfg["url"])
            if not raw:
                logger.error("Could not fetch %s — skipping", cfg["name"])
                continue

            body   = extract_gutenberg_body(raw)
            chunks = parse_into_chunks(body)

            if not chunks:
                logger.warning("No chunks parsed for %s", cfg["name"])
                continue

            logger.info("  %s: %d chunks parsed", cfg["name"], len(chunks))

            verses = [
                {
                    "religion":    RELIGION,
                    "text":        text,
                    "translation": cfg["translation"],
                    "book":        cfg["book"],
                    "chapter":     None,
                    "verse":       cidx + 1,
                    "reference":   f"{cfg['id_prefix']} {cidx + 1}",
                    "source_url":  cfg["url"],
                }
                for cidx, text in chunks
            ]

            total = 0
            for i in range(0, len(verses), BATCH_SIZE):
                batch      = verses[i : i + BATCH_SIZE]
                embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
                points = [
                    PointStruct(
                        id=str(uuid.uuid5(uuid.NAMESPACE_DNS,
                               f"Shinto:{cfg['id_prefix']}:{v['verse']}")),
                        vector=emb,
                        payload=v,
                    )
                    for v, emb in zip(batch, embeddings)
                ]
                client_q.upsert(collection_name=settings.qdrant_collection, points=points)
                total += len(points)

            grand_total += total
            logger.info("  %s: %d chunks ingested", cfg["name"], total)

    logger.info("Shinto ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_shinto())
