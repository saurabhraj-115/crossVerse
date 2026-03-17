"""
Ingest Jain scriptures from Sacred Texts Archive (Hermann Jacobi translation, Public Domain):
  - Uttaradhyayana Sutra (36 lectures) — core Jain ethics & philosophy
  - Acaranga Sutra (2 books) — oldest Jain text, Mahavira's asceticism

Source: Sacred Books of the East, Vols 22 & 45 (Oxford, Public Domain).
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

TEXTS = [
    {
        "name":        "Uttaradhyayana Sutra",
        "id_prefix":   "Uttaradhyayana",
        "translation": "Uttaradhyayana Sutra (Hermann Jacobi, Sacred Books of the East, Public Domain)",
        "pages": [
            ("https://www.sacred-texts.com/jai/su2/su201.htm", "Uttaradhyayana – Lecture 1"),
            ("https://www.sacred-texts.com/jai/su2/su202.htm", "Uttaradhyayana – Lecture 2"),
            ("https://www.sacred-texts.com/jai/su2/su203.htm", "Uttaradhyayana – Lecture 3"),
            ("https://www.sacred-texts.com/jai/su2/su204.htm", "Uttaradhyayana – Lecture 4"),
            ("https://www.sacred-texts.com/jai/su2/su205.htm", "Uttaradhyayana – Lecture 5"),
            ("https://www.sacred-texts.com/jai/su2/su206.htm", "Uttaradhyayana – Lecture 6"),
            ("https://www.sacred-texts.com/jai/su2/su207.htm", "Uttaradhyayana – Lecture 7"),
            ("https://www.sacred-texts.com/jai/su2/su208.htm", "Uttaradhyayana – Lecture 8"),
            ("https://www.sacred-texts.com/jai/su2/su209.htm", "Uttaradhyayana – Lecture 9"),
            ("https://www.sacred-texts.com/jai/su2/su210.htm", "Uttaradhyayana – Lecture 10"),
            ("https://www.sacred-texts.com/jai/su2/su211.htm", "Uttaradhyayana – Lecture 11"),
            ("https://www.sacred-texts.com/jai/su2/su212.htm", "Uttaradhyayana – Lecture 12"),
            ("https://www.sacred-texts.com/jai/su2/su213.htm", "Uttaradhyayana – Lecture 13"),
            ("https://www.sacred-texts.com/jai/su2/su214.htm", "Uttaradhyayana – Lecture 14"),
            ("https://www.sacred-texts.com/jai/su2/su215.htm", "Uttaradhyayana – Lecture 15"),
            ("https://www.sacred-texts.com/jai/su2/su216.htm", "Uttaradhyayana – Lecture 16"),
            ("https://www.sacred-texts.com/jai/su2/su217.htm", "Uttaradhyayana – Lecture 17"),
            ("https://www.sacred-texts.com/jai/su2/su218.htm", "Uttaradhyayana – Lecture 18"),
            ("https://www.sacred-texts.com/jai/su2/su219.htm", "Uttaradhyayana – Lecture 19"),
            ("https://www.sacred-texts.com/jai/su2/su220.htm", "Uttaradhyayana – Lecture 20"),
            ("https://www.sacred-texts.com/jai/su2/su221.htm", "Uttaradhyayana – Lecture 21"),
            ("https://www.sacred-texts.com/jai/su2/su222.htm", "Uttaradhyayana – Lecture 22"),
            ("https://www.sacred-texts.com/jai/su2/su223.htm", "Uttaradhyayana – Lecture 23"),
            ("https://www.sacred-texts.com/jai/su2/su224.htm", "Uttaradhyayana – Lecture 24"),
            ("https://www.sacred-texts.com/jai/su2/su225.htm", "Uttaradhyayana – Lecture 25"),
            ("https://www.sacred-texts.com/jai/su2/su226.htm", "Uttaradhyayana – Lecture 26"),
            ("https://www.sacred-texts.com/jai/su2/su227.htm", "Uttaradhyayana – Lecture 27"),
            ("https://www.sacred-texts.com/jai/su2/su228.htm", "Uttaradhyayana – Lecture 28"),
            ("https://www.sacred-texts.com/jai/su2/su229.htm", "Uttaradhyayana – Lecture 29"),
            ("https://www.sacred-texts.com/jai/su2/su230.htm", "Uttaradhyayana – Lecture 30"),
            ("https://www.sacred-texts.com/jai/su2/su231.htm", "Uttaradhyayana – Lecture 31"),
            ("https://www.sacred-texts.com/jai/su2/su232.htm", "Uttaradhyayana – Lecture 32"),
            ("https://www.sacred-texts.com/jai/su2/su233.htm", "Uttaradhyayana – Lecture 33"),
            ("https://www.sacred-texts.com/jai/su2/su234.htm", "Uttaradhyayana – Lecture 34"),
            ("https://www.sacred-texts.com/jai/su2/su235.htm", "Uttaradhyayana – Lecture 35"),
            ("https://www.sacred-texts.com/jai/su2/su236.htm", "Uttaradhyayana – Lecture 36"),
        ],
        "ref_fmt": "Uttaradhyayana {lec}:{v}",
    },
    {
        "name":        "Acaranga Sutra",
        "id_prefix":   "Acaranga",
        "translation": "Acaranga Sutra (Hermann Jacobi, Sacred Books of the East, Public Domain)",
        "pages": [
            ("https://www.sacred-texts.com/jai/su1/su101.htm", "Acaranga Sutra – Book 1, Lecture 1"),
            ("https://www.sacred-texts.com/jai/su1/su102.htm", "Acaranga Sutra – Book 1, Lecture 2"),
            ("https://www.sacred-texts.com/jai/su1/su103.htm", "Acaranga Sutra – Book 1, Lecture 3"),
            ("https://www.sacred-texts.com/jai/su1/su104.htm", "Acaranga Sutra – Book 1, Lecture 4"),
            ("https://www.sacred-texts.com/jai/su1/su105.htm", "Acaranga Sutra – Book 1, Lecture 5"),
            ("https://www.sacred-texts.com/jai/su1/su106.htm", "Acaranga Sutra – Book 1, Lecture 6"),
            ("https://www.sacred-texts.com/jai/su1/su107.htm", "Acaranga Sutra – Book 1, Lecture 7"),
            ("https://www.sacred-texts.com/jai/su1/su108.htm", "Acaranga Sutra – Book 1, Lecture 8"),
            ("https://www.sacred-texts.com/jai/su1/su109.htm", "Acaranga Sutra – Book 1, Lecture 9"),
            ("https://www.sacred-texts.com/jai/su1/su201.htm", "Acaranga Sutra – Book 2, Lecture 1"),
            ("https://www.sacred-texts.com/jai/su1/su202.htm", "Acaranga Sutra – Book 2, Lecture 2"),
            ("https://www.sacred-texts.com/jai/su1/su203.htm", "Acaranga Sutra – Book 2, Lecture 3"),
            ("https://www.sacred-texts.com/jai/su1/su204.htm", "Acaranga Sutra – Book 2, Lecture 4"),
            ("https://www.sacred-texts.com/jai/su1/su205.htm", "Acaranga Sutra – Book 2, Lecture 5"),
            ("https://www.sacred-texts.com/jai/su1/su206.htm", "Acaranga Sutra – Book 2, Lecture 6"),
        ],
        "ref_fmt": "Acaranga {lec}:{v}",
    },
]


def stable_id(prefix: str, lecture: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Jainism:{prefix}:{lecture}:{verse}"))


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


def clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_passages(html: str) -> list[str]:
    """Extract verse/paragraph passages from a Sacred-Texts Jain sutra page."""
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
            "footnote", "ftn", "[pg ", "p.", "sacred books"
        ]):
            continue
        passages.append(t)
    return passages


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


async def ingest_text(
    client_q: QdrantClient,
    settings,
    http: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    cfg: dict,
) -> int:
    logger.info("Ingesting %s…", cfg["name"])
    grand_total = 0

    for lec_idx, (url, book_name) in enumerate(cfg["pages"], start=1):
        html = await fetch_page(http, sem, url)
        if not html:
            logger.warning("  No content for lecture %d", lec_idx)
            continue

        passages = parse_passages(html)
        if not passages:
            logger.warning("  No passages for lecture %d", lec_idx)
            continue

        verses = []
        for v_idx, text in enumerate(passages, start=1):
            verses.append({
                "religion":    RELIGION,
                "text":        text,
                "translation": cfg["translation"],
                "book":        book_name,
                "chapter":     lec_idx,
                "verse":       v_idx,
                "reference":   cfg["ref_fmt"].format(lec=lec_idx, v=v_idx),
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
            grand_total += len(points)

        logger.info("  Lecture %d (%s): %d passages", lec_idx, book_name.split("–")[-1].strip(), len(verses))
        await asyncio.sleep(0.5)

    logger.info("%s complete: %d passages", cfg["name"], grand_total)
    return grand_total


async def ingest_jainism():
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

    logger.info("Jainism ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_jainism())
