"""
Ingest Jain scriptures from Project Gutenberg plain text (Public Domain):
  - Jain Sutras Part I: Acaranga Sutra + Kalpa Sutra (Hermann Jacobi, PG #8818)
  - Jain Sutras Part II: Uttaradhyayana Sutra + Sutrakritanga (Hermann Jacobi, PG #12459)

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

RELIGION   = "Jainism"
BATCH_SIZE = 20
MAX_WORDS  = 200   # target words per chunk

TEXTS = [
    {
        "url":         "https://www.gutenberg.org/cache/epub/8818/pg8818.txt",
        "name":        "Jain Sutras Part I (Acaranga + Kalpa Sutra)",
        "id_prefix":   "JainSutras1",
        "translation": "Jain Sutras Part I (Hermann Jacobi, Sacred Books of the East, Public Domain)",
        "book_default": "Acaranga Sutra",
        "ref_prefix":  "Jain Sutras I",
    },
    {
        "url":         "https://www.gutenberg.org/cache/epub/12459/pg12459.txt",
        "name":        "Jain Sutras Part II (Uttaradhyayana + Sutrakritanga)",
        "id_prefix":   "JainSutras2",
        "translation": "Jain Sutras Part II (Hermann Jacobi, Sacred Books of the East, Public Domain)",
        "book_default": "Uttaradhyayana Sutra",
        "ref_prefix":  "Jain Sutras II",
    },
]


def stable_id(prefix: str, chunk_idx: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Jainism:{prefix}:{chunk_idx}"))


def clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_gutenberg_body(raw: str) -> str:
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    start = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG", raw, re.IGNORECASE)
    end   = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG", raw, re.IGNORECASE)
    if start and end:
        return raw[start.end():end.start()]
    return raw


def parse_into_chunks(body: str, max_words: int = MAX_WORDS) -> list[tuple[str, int, str]]:
    """
    Parse a Jacobi Jain sutra plain text into word-capped chunks.
    Returns list of (book_name, chunk_idx, text).

    Legge/Jacobi texts use headings like "LECTURE 1." / "BOOK I." / "CHAPTER I."
    followed by numbered paragraphs.
    """
    lines = body.splitlines()
    chunks: list[tuple[str, int, str]] = []

    # Track current book section name
    current_book   = ""
    chunk_idx      = 0
    buf_words: list[str] = []
    buf_parts: list[str] = []

    # Section heading patterns
    heading_re = re.compile(
        r"^\s*(LECTURE|BOOK|CHAPTER|PART|SUTRA|LESSON)\s+([IVXLC\d]+)\.?\s*$",
        re.IGNORECASE,
    )
    # Numbered paragraph: "1. The ..." or "1) The ..."
    numbered_re = re.compile(r"^\s*\d+[\.\)]\s+\S")

    skip_kws = {
        "gutenberg", "transcriber", "footnote", "produced by", "ebook",
        "www.gutenberg", "online distributed", "public domain"
    }

    def flush():
        nonlocal chunk_idx
        if buf_parts:
            text = clean_ws(" ".join(buf_parts))
            if len(text) > 30:
                chunks.append((current_book or "Jain Sutras", chunk_idx, text))
                chunk_idx += 1
            buf_words.clear()
            buf_parts.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(kw in stripped.lower() for kw in skip_kws):
            continue

        # Detect section heading
        m = heading_re.match(stripped)
        if m:
            flush()
            label = f"{m.group(1).title()} {m.group(2)}"
            current_book = label
            continue

        # Detect numbered paragraph start → flush if big enough
        if numbered_re.match(line) and buf_words:
            words = stripped.split()
            if len(buf_words) + len(words) > max_words:
                flush()

        words = stripped.split()
        if len(buf_words) + len(words) > max_words and buf_words:
            flush()

        buf_words.extend(words)
        buf_parts.append(stripped)

    flush()
    return chunks


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

    body   = extract_gutenberg_body(raw)
    chunks = parse_into_chunks(body)

    if not chunks:
        logger.warning("No chunks parsed for %s", cfg["name"])
        return 0

    logger.info("  %s: %d chunks parsed", cfg["name"], len(chunks))

    verses = [
        {
            "religion":    RELIGION,
            "text":        text,
            "translation": cfg["translation"],
            "book":        book_name,
            "chapter":     None,
            "verse":       chunk_idx + 1,
            "reference":   f"{cfg['ref_prefix']} {chunk_idx + 1}",
            "source_url":  cfg["url"],
        }
        for book_name, chunk_idx, text in chunks
    ]

    total = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch      = verses[i : i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(
                id=stable_id(cfg["id_prefix"], v["verse"]),
                vector=emb,
                payload=v,
            )
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)

    logger.info("  %s: %d chunks ingested", cfg["name"], total)
    return total


async def ingest_jainism():
    settings    = get_settings()
    client_q    = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem         = asyncio.Semaphore(4)
    grand_total = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": "CrossVerse-Ingestion/1.0"},
        follow_redirects=True,
    ) as http:
        for cfg in TEXTS:
            total = await ingest_text(client_q, settings, http, sem, cfg)
            grand_total += total

    logger.info("Jainism ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_jainism())
