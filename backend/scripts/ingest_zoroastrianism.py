"""
Ingest Zoroastrian scriptures from Project Gutenberg + Sacred Texts Archive (Public Domain):
  - Vendidad / Videvdat (James Darmesteter, SBE Vol 4) — 22 fargards ✓ Sacred Texts
  - Yasna + Gathas (L.H. Mills, SBE Vol 31, PG #56968) — from Gutenberg
  - Khordeh Avesta fragments where available

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

RELIGION   = "Zoroastrianism"
BATCH_SIZE = 20

# Sacred Texts Archive — Vendidad (confirmed working with httpx User-Agent)
VENDIDAD_PAGES = [
    (f"https://www.sacred-texts.com/zor/sbe04/sbe04{n:02d}.htm",
     f"Vendidad – Fargard {n}",
     n)
    for n in range(1, 23)
]

# Project Gutenberg — Avestan texts (plain text, no JS required)
# SBE Vol 23 (Yasna + Vispered + Vendidad, Darmesteter) — PG #2131
# Sacred Hymns and Proverbs (Mills) — may not have its own PG entry
# We use the Sacred Books of the East Vol 31 via Avesta.org mirror or similar
GUTENBERG_TEXTS = [
    {
        "url":         "https://www.gutenberg.org/cache/epub/2131/pg2131.txt",
        "name":        "The Zend-Avesta Part I (Vendidad, Darmesteter)",
        "id_prefix":   "ZendAvesta1",
        "translation": "The Zend-Avesta (James Darmesteter, Sacred Books of the East, Public Domain)",
        "ref_prefix":  "Avesta",
    },
]


def stable_id(prefix: str, chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Zoroastrianism:{prefix}:{chapter}:{verse}"))


def stable_id_chunk(prefix: str, idx: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Zoroastrianism:{prefix}:chunk:{idx}"))


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


def clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


async def fetch_page(client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str) -> str:
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=30)
                if r.status_code == 200:
                    return r.text
                if r.status_code == 404:
                    return ""
            except Exception as e:
                if attempt == 2:
                    logger.warning("Failed %s — %s", url, e)
                await asyncio.sleep(2 ** attempt)
    return ""


def parse_html_passages(html: str) -> list[str]:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    p_blocks = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)
    passages: list[str] = []
    for block in p_blocks:
        t = clean_ws(strip_html(block))
        if len(t) < 30:
            continue
        lower = t.lower()
        if any(kw in lower for kw in [
            "sacred-texts.com", "next", "previous", "contents", "copyright",
            "footnote", "ftn", "[pg ", "sacred books of the east"
        ]):
            continue
        passages.append(t)
    return passages


def extract_gutenberg_body(raw: str) -> str:
    start = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG", raw, re.IGNORECASE)
    end   = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG", raw, re.IGNORECASE)
    if start and end:
        return raw[start.end():end.start()]
    return raw


def parse_gutenberg_chunks(body: str, max_words: int = 200) -> list[tuple[str, int, str]]:
    """Word-capped chunks from plain text, tracking section headings."""
    lines = body.splitlines()
    chunks: list[tuple[str, int, str]] = []

    current_section = "Avesta"
    chunk_idx       = 0
    buf_words: list[str] = []
    buf_parts: list[str] = []

    heading_re = re.compile(
        r"^\s*(FARGARD|YASNA|CHAPTER|SECTION|PART|GATHA)\s+([IVXLC\d]+\.?)\s*$",
        re.IGNORECASE,
    )
    skip_kws = {"gutenberg", "transcriber", "produced by", "ebook", "www.gutenberg"}

    def flush():
        nonlocal chunk_idx
        if buf_parts:
            text = clean_ws(" ".join(buf_parts))
            if len(text) > 30:
                chunks.append((current_section, chunk_idx, text))
                chunk_idx += 1
            buf_words.clear()
            buf_parts.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(kw in stripped.lower() for kw in skip_kws):
            continue

        m = heading_re.match(stripped)
        if m:
            flush()
            current_section = f"{m.group(1).title()} {m.group(2).strip('.')}"
            continue

        words = stripped.split()
        if len(buf_words) + len(words) > max_words and buf_words:
            flush()
        buf_words.extend(words)
        buf_parts.append(stripped)

    flush()
    return chunks


async def ingest_vendidad(
    client_q: QdrantClient, settings, http: httpx.AsyncClient, sem: asyncio.Semaphore
) -> int:
    logger.info("Ingesting Vendidad (Sacred Texts)…")
    grand_total = 0

    for url, book_name, chap_num in VENDIDAD_PAGES:
        html = await fetch_page(http, sem, url)
        if not html:
            logger.warning("  No content for %s", book_name)
            continue

        passages = parse_html_passages(html)
        if not passages:
            logger.warning("  No passages for %s", book_name)
            continue

        verses = [
            {
                "religion":    RELIGION,
                "text":        text,
                "translation": "Vendidad (James Darmesteter, Sacred Books of the East, Public Domain)",
                "book":        book_name,
                "chapter":     chap_num,
                "verse":       v_idx,
                "reference":   f"Vendidad {chap_num}:{v_idx}",
                "source_url":  url,
            }
            for v_idx, text in enumerate(passages, start=1)
        ]

        for i in range(0, len(verses), BATCH_SIZE):
            batch      = verses[i : i + BATCH_SIZE]
            embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
            points = [
                PointStruct(
                    id=stable_id("Vendidad", v["chapter"], v["verse"]),
                    vector=emb,
                    payload=v,
                )
                for v, emb in zip(batch, embeddings)
            ]
            client_q.upsert(collection_name=settings.qdrant_collection, points=points)
            grand_total += len(points)

        logger.info("  %s: %d passages", book_name, len(verses))
        await asyncio.sleep(0.5)

    logger.info("Vendidad complete: %d passages", grand_total)
    return grand_total


async def ingest_gutenberg_text(
    client_q: QdrantClient,
    settings,
    http: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    cfg: dict,
) -> int:
    logger.info("Fetching %s from Gutenberg…", cfg["name"])
    raw = await fetch_page(http, sem, cfg["url"])
    if not raw:
        logger.warning("Could not fetch %s", cfg["name"])
        return 0

    body   = extract_gutenberg_body(raw)
    chunks = parse_gutenberg_chunks(body)
    if not chunks:
        logger.warning("No chunks for %s", cfg["name"])
        return 0

    logger.info("  %s: %d chunks", cfg["name"], len(chunks))

    verses = [
        {
            "religion":    RELIGION,
            "text":        text,
            "translation": cfg["translation"],
            "book":        section,
            "chapter":     None,
            "verse":       idx + 1,
            "reference":   f"{cfg['ref_prefix']} {idx + 1}",
            "source_url":  cfg["url"],
        }
        for section, idx, text in chunks
    ]

    total = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch      = verses[i : i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(
                id=stable_id_chunk(cfg["id_prefix"], v["verse"]),
                vector=emb,
                payload=v,
            )
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)

    logger.info("  %s: %d chunks ingested", cfg["name"], total)
    return total


async def ingest_zoroastrianism():
    settings    = get_settings()
    client_q    = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem         = asyncio.Semaphore(3)
    grand_total = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": "CrossVerse-Ingestion/1.0"},
        follow_redirects=True,
    ) as http:
        # Vendidad from Sacred Texts (already confirmed working)
        vendidad_total = await ingest_vendidad(client_q, settings, http, sem)
        grand_total += vendidad_total

        # Additional Avestan texts from Gutenberg
        for cfg in GUTENBERG_TEXTS:
            total = await ingest_gutenberg_text(client_q, settings, http, sem, cfg)
            grand_total += total

    logger.info("Zoroastrianism ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_zoroastrianism())
