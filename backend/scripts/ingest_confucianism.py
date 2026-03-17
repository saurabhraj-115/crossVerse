"""
Ingest Confucian scriptures from Sacred Texts Archive (James Legge translations, Public Domain):
  - Analects of Confucius (20 books, ~500 passages)
  - Mencius (7 books, ~300 passages)

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

RELIGION    = "Confucianism"
BATCH_SIZE  = 20

TEXTS = [
    {
        "name":        "Analects of Confucius",
        "id_prefix":   "Analects",
        "translation": "Analects of Confucius (James Legge, Public Domain)",
        "num_books":   20,
        "url_pattern": "https://www.sacred-texts.com/cfu/conf{n}.htm",
        "book_fmt":    "Analects – Book {n}",
        "ref_fmt":     "Analects {n}:{v}",
    },
    {
        "name":        "Mencius",
        "id_prefix":   "Mencius",
        "translation": "Mencius (James Legge, Public Domain)",
        "num_books":   7,
        "url_pattern": "https://www.sacred-texts.com/cfu/menc{n}.htm",
        "book_fmt":    "Mencius – Book {n}",
        "ref_fmt":     "Mencius {n}:{v}",
    },
]


def stable_id(prefix: str, book: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Confucianism:{prefix}:{book}:{verse}"))


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


def clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_passages(html: str) -> list[str]:
    """
    Extract verse-level passages from a Sacred-Texts Analects/Mencius page.
    Passages are wrapped in <p> tags and begin with a bold number pattern like:
      <p><b>I. 1.</b> ...text... </p>
      <p><b>1.</b> ...text... </p>
    We collect any <p> that contains a leading bold/number indicator.
    """
    passages: list[str] = []

    # Match <p>...</p> blocks (non-greedy, may span tags)
    p_blocks = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)
    for block in p_blocks:
        raw = strip_html(block)
        text = clean_ws(raw)
        # Must be substantive (>30 chars) and start with a roman/arabic numeral or bold marker
        if len(text) < 30:
            continue
        # Filter out navigation, header lines, attribution lines
        lower = text.lower()
        if any(kw in lower for kw in ["sacred-texts.com", "next", "previous", "contents", "index", "copyright"]):
            continue
        # Keep passages that look like verse text (start with digit, roman numeral, or quote)
        if re.match(r"^(I{1,3}V?|V?I{0,3}[IVX]\.?\s|\d+\.?\s|[\"'\u201c])", text):
            passages.append(text)
        elif len(text) > 60 and not re.match(r"^(chapter|book|part|section)", lower):
            # Also keep longer blocks that aren't headers
            passages.append(text)

    return passages


async def fetch_page(
    client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str
) -> str:
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


async def ingest_text(
    client_q: QdrantClient,
    settings,
    http: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    cfg: dict,
) -> int:
    logger.info("Ingesting %s…", cfg["name"])
    total = 0

    for book_num in range(1, cfg["num_books"] + 1):
        url = cfg["url_pattern"].format(n=book_num)
        html = await fetch_page(http, sem, url)
        if not html:
            logger.warning("  No content for %s book %d", cfg["name"], book_num)
            continue

        passages = parse_passages(html)
        if not passages:
            logger.warning("  No passages parsed for %s book %d", cfg["name"], book_num)
            continue

        verses = []
        for v_idx, text in enumerate(passages, start=1):
            verses.append({
                "religion":    RELIGION,
                "text":        text,
                "translation": cfg["translation"],
                "book":        cfg["book_fmt"].format(n=book_num),
                "chapter":     book_num,
                "verse":       v_idx,
                "reference":   cfg["ref_fmt"].format(n=book_num, v=v_idx),
                "source_url":  url,
            })

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

        logger.info("  %s Book %d: %d passages", cfg["name"], book_num, len(verses))
        await asyncio.sleep(0.5)   # polite crawl delay

    logger.info("%s complete: %d passages", cfg["name"], total)
    return total


async def ingest_confucianism():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem      = asyncio.Semaphore(3)
    grand_total = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": "CrossVerse-Ingestion/1.0"},
        follow_redirects=True,
    ) as http:
        for cfg in TEXTS:
            total = await ingest_text(client_q, settings, http, sem, cfg)
            grand_total += total

    logger.info("Confucianism ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_confucianism())
