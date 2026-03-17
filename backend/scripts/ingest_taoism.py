"""
Ingest Taoist scriptures from Sacred Texts Archive (Public Domain translations):
  - Tao Te Ching / Tao Teh King (James Legge, SBE Vol 39) — 81 chapters
  - Writings of Chuang Tzu / Zhuangzi (James Legge, SBE Vol 39/40) — 33 inner+outer books

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

RELIGION   = "Taoism"
BATCH_SIZE = 20

# Tao Te Ching — single page with all 81 chapters
TAO_TE_CHING_URL = "https://www.sacred-texts.com/tao/taote.htm"

# Chuang Tzu inner chapters (most authentic) — pages at Sacred Texts
CHUANG_TZU_PAGES = [
    ("https://www.sacred-texts.com/tao/sbe39/sbe3901.htm", "Zhuangzi – Book 1: Free and Easy Wandering"),
    ("https://www.sacred-texts.com/tao/sbe39/sbe3902.htm", "Zhuangzi – Book 2: The Adjustment of Controversies"),
    ("https://www.sacred-texts.com/tao/sbe39/sbe3903.htm", "Zhuangzi – Book 3: Nourishing the Lord of Life"),
    ("https://www.sacred-texts.com/tao/sbe39/sbe3904.htm", "Zhuangzi – Book 4: Man in the World, Associated with other Men"),
    ("https://www.sacred-texts.com/tao/sbe39/sbe3905.htm", "Zhuangzi – Book 5: The Sign of Virtue Complete"),
    ("https://www.sacred-texts.com/tao/sbe39/sbe3906.htm", "Zhuangzi – Book 6: The Great and Most Honoured Master"),
    ("https://www.sacred-texts.com/tao/sbe39/sbe3907.htm", "Zhuangzi – Book 7: The Normal Course for Rulers and Kings"),
]


def stable_id(prefix: str, chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Taoism:{prefix}:{chapter}:{verse}"))


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


def clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


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


def parse_ttc_chapters(html: str) -> list[tuple[int, str]]:
    """
    Parse all 81 chapters from the Tao Te Ching page.
    Each chapter is enclosed in a <div> or set of <p> tags preceded by a chapter heading.
    Returns list of (chapter_number, text).
    """
    chapters: list[tuple[int, str]] = []

    # Find chapter headings like "CHAPTER I." or "1."
    # Sacred Texts Tao Te Ching page uses <h3> or <b> for chapter numbers,
    # followed by one or more <p> tags with the verse text.
    # Strategy: split by chapter markers and extract text blocks.

    # Remove script/style tags
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Split on chapter headings (various formats used on the page)
    # Pattern: "CHAPTER I", "CHAPTER 1", Roman numerals in headers
    chapter_splits = re.split(
        r"(?:CHAPTER\s+[IVXLC]+\.?|<h[23][^>]*>[^<]*CHAPTER\s+|<h[23][^>]*>\s*\d+\s*</h[23]>)",
        html,
        flags=re.IGNORECASE,
    )

    if len(chapter_splits) < 10:
        # Fallback: split on <hr> tags which often separate chapters
        chapter_splits = re.split(r"<hr\s*/?>", html, flags=re.IGNORECASE)

    chap_num = 0
    for segment in chapter_splits[1:]:   # skip preamble
        chap_num += 1
        if chap_num > 81:
            break
        # Extract all <p> text from this segment
        p_blocks = re.findall(r"<p[^>]*>(.*?)</p>", segment, re.DOTALL | re.IGNORECASE)
        texts = []
        for block in p_blocks:
            t = clean_ws(strip_html(block))
            if len(t) < 15:
                continue
            lower = t.lower()
            if any(kw in lower for kw in ["sacred-texts", "next chapter", "previous", "contents", "copyright"]):
                continue
            texts.append(t)
        combined = " ".join(texts)
        if len(combined) > 20:
            chapters.append((chap_num, combined))

    return chapters


def parse_prose_passages(html: str) -> list[str]:
    """
    Extract substantive paragraphs from a Chuang Tzu / prose philosophy page.
    Returns list of passage strings.
    """
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    p_blocks = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)

    passages: list[str] = []
    for block in p_blocks:
        t = clean_ws(strip_html(block))
        if len(t) < 40:
            continue
        lower = t.lower()
        if any(kw in lower for kw in ["sacred-texts.com", "next", "previous", "contents", "copyright", "footnote"]):
            continue
        passages.append(t)
    return passages


async def ingest_tao_te_ching(
    client_q: QdrantClient, settings, http: httpx.AsyncClient, sem: asyncio.Semaphore
) -> int:
    logger.info("Ingesting Tao Te Ching…")
    html = await fetch_page(http, sem, TAO_TE_CHING_URL)
    if not html:
        logger.error("Failed to fetch Tao Te Ching page")
        return 0

    chapters = parse_ttc_chapters(html)
    if not chapters:
        logger.warning("No chapters parsed from Tao Te Ching — falling back to paragraph parse")
        # Fallback: treat each <p> as a verse
        passages = parse_prose_passages(html)
        chapters = [(i + 1, t) for i, t in enumerate(passages[:81])]

    logger.info("  Tao Te Ching: %d chapters parsed", len(chapters))

    verses = []
    for chap_num, text in chapters:
        verses.append({
            "religion":    RELIGION,
            "text":        text,
            "translation": "Tao Te Ching (James Legge, Public Domain)",
            "book":        "Tao Te Ching",
            "chapter":     chap_num,
            "verse":       1,
            "reference":   f"Tao Te Ching {chap_num}",
            "source_url":  TAO_TE_CHING_URL,
        })

    total = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch      = verses[i : i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(
                id=stable_id("TTC", v["chapter"], v["verse"]),
                vector=emb,
                payload=v,
            )
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)

    logger.info("  Tao Te Ching: %d chapters ingested", total)
    return total


async def ingest_chuang_tzu(
    client_q: QdrantClient, settings, http: httpx.AsyncClient, sem: asyncio.Semaphore
) -> int:
    logger.info("Ingesting Zhuangzi inner chapters…")
    grand_total = 0

    for book_idx, (url, book_name) in enumerate(CHUANG_TZU_PAGES, start=1):
        html = await fetch_page(http, sem, url)
        if not html:
            logger.warning("  No content for %s", book_name)
            continue

        passages = parse_prose_passages(html)
        if not passages:
            logger.warning("  No passages for %s", book_name)
            continue

        verses = []
        for v_idx, text in enumerate(passages, start=1):
            verses.append({
                "religion":    RELIGION,
                "text":        text,
                "translation": "Zhuangzi / Writings of Chuang Tzu (James Legge, Public Domain)",
                "book":        book_name,
                "chapter":     book_idx,
                "verse":       v_idx,
                "reference":   f"Zhuangzi {book_idx}:{v_idx}",
                "source_url":  url,
            })

        total = 0
        for i in range(0, len(verses), BATCH_SIZE):
            batch      = verses[i : i + BATCH_SIZE]
            embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
            points = [
                PointStruct(
                    id=stable_id("Zhuangzi", v["chapter"], v["verse"]),
                    vector=emb,
                    payload=v,
                )
                for v, emb in zip(batch, embeddings)
            ]
            client_q.upsert(collection_name=settings.qdrant_collection, points=points)
            total += len(points)

        grand_total += total
        logger.info("  %s: %d passages", book_name, total)
        await asyncio.sleep(0.5)

    logger.info("Zhuangzi complete: %d passages", grand_total)
    return grand_total


async def ingest_taoism():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem      = asyncio.Semaphore(3)

    async with httpx.AsyncClient(
        headers={"User-Agent": "CrossVerse-Ingestion/1.0"},
        follow_redirects=True,
    ) as http:
        ttc_total = await ingest_tao_te_ching(client_q, settings, http, sem)
        czz_total = await ingest_chuang_tzu(client_q, settings, http, sem)

    logger.info(
        "Taoism ingestion complete. Tao Te Ching=%d  Zhuangzi=%d  Total=%d",
        ttc_total, czz_total, ttc_total + czz_total,
    )


if __name__ == "__main__":
    asyncio.run(ingest_taoism())
