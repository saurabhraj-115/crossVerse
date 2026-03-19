"""
Ingest Confucian scriptures from Project Gutenberg plain text (Public Domain):
  - Analects of Confucius — James Legge translation (PG #4094)
  - The Great Learning + The Doctrine of the Mean — James Legge (PG #4094)

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

RELIGION   = "Confucianism"
BATCH_SIZE = 20

# Project Gutenberg plain-text files (Public Domain)
GUTENBERG_URLS = [
    {
        "url":         "https://www.gutenberg.org/cache/epub/4094/pg4094.txt",
        "name":        "The Analects of Confucius",
        "id_prefix":   "Analects",
        "translation": "The Analects of Confucius (James Legge, Public Domain)",
        "book_base":   "Analects",
        "ref_prefix":  "Analects",
    },
    {
        "url":         "https://www.gutenberg.org/cache/epub/4095/pg4095.txt",
        "name":        "The Great Learning",
        "id_prefix":   "GreatLearning",
        "translation": "The Great Learning (James Legge, Public Domain)",
        "book_base":   "The Great Learning",
        "ref_prefix":  "Great Learning",
    },
    {
        "url":         "https://www.gutenberg.org/cache/epub/4096/pg4096.txt",
        "name":        "The Doctrine of the Mean",
        "id_prefix":   "DocMean",
        "translation": "The Doctrine of the Mean (James Legge, Public Domain)",
        "book_base":   "The Doctrine of the Mean",
        "ref_prefix":  "Doctrine of the Mean",
    },
]


def stable_id(prefix: str, chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Confucianism:{prefix}:{chapter}:{verse}"))


def clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_gutenberg_body(raw: str) -> str:
    """Strip Project Gutenberg header/footer, return body text."""
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    start = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG", raw, re.IGNORECASE)
    end   = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG", raw, re.IGNORECASE)
    if start and end:
        return raw[start.end():end.start()]
    return raw


def parse_into_passages(body: str, max_words: int = 150) -> list[tuple[int, int, str]]:
    """
    Split a Legge plain-text translation into (chapter, verse, text) tuples.

    Legge uses paragraph numbering like:
      1.  The Master said, ...
      2.  He said, ...
    or book headings like "BOOK I. HSUEH ERH."

    Strategy: accumulate lines until a numbered paragraph boundary, then flush.
    Returns list of (chapter_idx, verse_idx, text).
    """
    lines = body.splitlines()
    passages: list[tuple[int, int, str]] = []

    chapter_idx = 0
    verse_idx   = 0
    buf: list[str] = []

    # Detect numbered paragraph: line starts with digit(s) + period (or Roman numeral)
    para_re = re.compile(r"^\s*(\d+)\.\s+\S")

    def flush_buf():
        nonlocal verse_idx
        text = clean_ws(" ".join(buf))
        if text and len(text) > 20:
            verse_idx += 1
            passages.append((max(chapter_idx, 1), verse_idx, text))
        buf.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect chapter/book heading
        if re.match(r"^(BOOK|CHAPTER|PART)\s+[IVXLC\d]+", stripped, re.IGNORECASE):
            flush_buf()
            chapter_idx += 1
            verse_idx = 0
            continue

        # Detect numbered verse start
        m = para_re.match(line)
        if m:
            flush_buf()
            # Start a new passage
            buf.append(stripped)
        else:
            # Skip pure header/navigation lines
            if any(kw in stripped.lower() for kw in [
                "gutenberg", "project gutenberg", "transcriber", "footnote",
                "produced by", "www.gutenberg", "ebook"
            ]):
                continue
            if buf:
                buf.append(stripped)

    flush_buf()
    return passages


async def fetch_text(client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str) -> str:
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=60)
                if r.status_code == 200:
                    return r.text
                if r.status_code == 404:
                    return ""
            except Exception as e:
                if attempt == 2:
                    logger.warning("Failed %s — %s", url, e)
                await asyncio.sleep(2 ** attempt)
    return ""


async def ingest_text(
    client_q: QdrantClient,
    settings,
    http: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    cfg: dict,
) -> int:
    logger.info("Fetching %s…", cfg["name"])
    raw = await fetch_text(http, sem, cfg["url"])
    if not raw:
        logger.error("Could not fetch %s", cfg["name"])
        return 0

    body     = extract_gutenberg_body(raw)
    passages = parse_into_passages(body)

    if not passages:
        logger.warning("No passages parsed for %s", cfg["name"])
        return 0

    logger.info("  %s: %d passages parsed", cfg["name"], len(passages))

    verses = [
        {
            "religion":    RELIGION,
            "text":        text,
            "translation": cfg["translation"],
            "book":        f"{cfg['book_base']} – Book {chap}",
            "chapter":     chap,
            "verse":       verse,
            "reference":   f"{cfg['ref_prefix']} {chap}:{verse}",
            "source_url":  cfg["url"],
        }
        for chap, verse, text in passages
    ]

    total = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch      = verses[i : i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(
                id=stable_id(cfg["id_prefix"], v["chapter"], v["verse"]),
                vector=emb,
                payload=v,
            )
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)

    logger.info("  %s: %d passages ingested", cfg["name"], total)
    return total


async def ingest_confucianism():
    settings    = get_settings()
    client_q    = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem         = asyncio.Semaphore(4)
    grand_total = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": "CrossVerse-Ingestion/1.0"},
        follow_redirects=True,
    ) as http:
        for cfg in GUTENBERG_URLS:
            total = await ingest_text(client_q, settings, http, sem, cfg)
            grand_total += total

    logger.info("Confucianism ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_confucianism())
