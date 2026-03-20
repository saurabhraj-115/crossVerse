"""
Ingest Jain scriptures from wisdomlib.org (Jacobi translations, public domain):
  - Acaranga Sutra     — 81 sections  (Hermann Jacobi, Sacred Books of the East)
  - Uttaradhyayana Sutra — 37 sections (Hermann Jacobi, Sacred Books of the East)

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
MAX_WORDS  = 200

WISDOMLIB_BASE = "https://www.wisdomlib.org"

BOOKS = [
    {
        "index_url":   "https://www.wisdomlib.org/jainism/book/acaranga-sutra",
        "link_pattern": r"/jainism/book/acaranga-sutra/d/doc\d+\.html",
        "name":        "Acaranga Sutra",
        "id_prefix":   "AcarangaSutra",
        "translation": "Acaranga Sutra (Hermann Jacobi, Sacred Books of the East, Public Domain)",
        "book":        "Acaranga Sutra",
    },
    {
        "index_url":   "https://www.wisdomlib.org/jainism/book/uttaradhyayana-sutra",
        "link_pattern": r"/jainism/book/uttaradhyayana-sutra/d/doc\d+\.html",
        "name":        "Uttaradhyayana Sutra",
        "id_prefix":   "UttaradhyayanaSutra",
        "translation": "Uttaradhyayana Sutra (Hermann Jacobi, Sacred Books of the East, Public Domain)",
        "book":        "Uttaradhyayana Sutra",
    },
]

# HTML extraction: strip tags + clean footnote markers
_TAG_RE      = re.compile(r"<[^>]+>")
_ENTITY_RE   = re.compile(r"&[a-z#0-9]+;")
_FOOTNOTE_RE = re.compile(r"\[\d+\]")


def extract_page_text(html: str) -> str:
    """
    Strip HTML tags, entities, and footnote markers from a wisdomlib chapter page.
    Returns cleaned plain text.
    """
    # Remove script, style, nav, footer blocks entirely
    for tag in ("script", "style", "nav", "footer", "header", "aside"):
        html = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # Strip remaining tags
    text = _TAG_RE.sub(" ", html)
    text = _ENTITY_RE.sub(" ", text)
    text = _FOOTNOTE_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Find the scripture body: look for the first numbered paragraph (e.g. "1. " or "1)")
    # or a heading like "Lecture X" / "Lesson X"
    m = re.search(r"(?:Lecture|Lesson|Lecture\s+\d|^\d+[.\)])\s+\d", text)
    if m:
        # Take from just before that match to cut navigation preamble
        text = text[max(0, m.start() - 50):]

    # Cut off footnotes section if present
    fn_match = re.search(r"Footnotes?\s*\d", text, re.IGNORECASE)
    if fn_match:
        text = text[:fn_match.start()]

    return text.strip()


def build_chunks(text: str, book: str, id_prefix: str, base_chunk_idx: int) -> list[dict]:
    """Split page text into ~MAX_WORDS chunks."""
    chunks: list[dict] = []
    words = text.split()
    chunk_idx = base_chunk_idx

    for i in range(0, len(words), MAX_WORDS):
        chunk_words = words[i : i + MAX_WORDS]
        chunk_text  = " ".join(chunk_words).strip()
        if len(chunk_words) < 8:
            continue
        chunks.append({
            "religion":    RELIGION,
            "text":        chunk_text,
            "translation": "",           # filled in by caller
            "book":        book,
            "chapter":     None,
            "verse":       chunk_idx + 1,
            "reference":   f"{id_prefix} {chunk_idx + 1}",
            "source_url":  "",           # filled in by caller
            "_id":         str(uuid.uuid5(uuid.NAMESPACE_DNS,
                                          f"Jainism:{id_prefix}:{chunk_idx}")),
        })
        chunk_idx += 1

    return chunks


async def fetch_html(client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str) -> str:
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=30)
                if r.status_code == 200:
                    return r.text
                if r.status_code == 404:
                    return ""
            except Exception as e:
                logger.warning("fetch attempt %d: %s — %s", attempt + 1, url, e)
                await asyncio.sleep(2 ** attempt)
    return ""


async def ingest_book(
    client_q: QdrantClient,
    settings,
    http: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    cfg: dict,
) -> int:
    logger.info("Fetching index: %s", cfg["name"])
    index_html = await fetch_html(http, sem, cfg["index_url"])
    if not index_html:
        logger.error("Could not fetch index for %s", cfg["name"])
        return 0

    # Discover chapter links
    links = list(dict.fromkeys(
        re.findall(cfg["link_pattern"], index_html)
    ))
    logger.info("  %s: %d chapter pages discovered", cfg["name"], len(links))
    if not links:
        return 0

    all_chunks: list[dict] = []
    chunk_base = 0

    for link in links:
        url = WISDOMLIB_BASE + link
        html = await fetch_html(http, sem, url)
        if not html:
            continue
        await asyncio.sleep(0.3)   # polite delay

        text = extract_page_text(html)
        if len(text.split()) < 8:
            continue

        page_chunks = build_chunks(text, cfg["book"], cfg["id_prefix"], chunk_base)
        # Fill in translation + source_url
        for c in page_chunks:
            c["translation"] = cfg["translation"]
            c["source_url"]  = url
        all_chunks.extend(page_chunks)
        chunk_base += len(page_chunks)

    logger.info("  %s: %d chunks from %d pages", cfg["name"], len(all_chunks), len(links))

    total = 0
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        embeddings = await embed_texts([c["text"] for c in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(id=c.pop("_id"), vector=emb, payload=c)
            for c, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)

        if (i // BATCH_SIZE) % 10 == 0:
            logger.info("  %s: ingested %d / %d chunks…", cfg["name"], total, len(all_chunks))

    logger.info("  %s: %d chunks ingested", cfg["name"], total)
    return total


async def ingest_jainism():
    settings    = get_settings()
    client_q    = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem         = asyncio.Semaphore(4)
    grand_total = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": "CrossVerse-Ingestion/1.0 (academic research)"},
        follow_redirects=True,
        timeout=30,
    ) as http:
        for cfg in BOOKS:
            total = await ingest_book(client_q, settings, http, sem, cfg)
            grand_total += total

    logger.info("Jainism ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_jainism())
