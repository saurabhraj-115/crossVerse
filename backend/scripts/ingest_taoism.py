"""
Ingest Taoist scriptures from Project Gutenberg plain text (Public Domain):
  - Tao Te Ching (James Legge, PG #216) — 81 chapters
  - Tao Teh King / Lao-Tze's Tao and Wu Wei (alternate Suzuki/Carus, PG #7005) — 81 chapters

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

TEXTS = [
    {
        "url":         "https://www.gutenberg.org/cache/epub/216/pg216.txt",
        "name":        "Tao Te Ching (James Legge)",
        "id_prefix":   "TTC_Legge",
        "translation": "Tao Te Ching (James Legge, Public Domain)",
        "book":        "Tao Te Ching",
        "ref_prefix":  "Tao Te Ching",
    },
    {
        "url":         "https://www.gutenberg.org/cache/epub/7005/pg7005.txt",
        "name":        "Tao Te Ching (Suzuki & Carus)",
        "id_prefix":   "TTC_Carus",
        "translation": "Tao Te Ching (Suzuki & Carus, Public Domain)",
        "book":        "Tao Te Ching",
        "ref_prefix":  "Tao Te Ching",
    },
]


def stable_id(prefix: str, chapter: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Taoism:{prefix}:{chapter}"))


def clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_gutenberg_body(raw: str) -> str:
    # Normalize line endings first
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    start = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG", raw, re.IGNORECASE)
    end   = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG", raw, re.IGNORECASE)
    if start and end:
        return raw[start.end():end.start()]
    return raw


def parse_ttc_chapters(body: str) -> list[tuple[int, str]]:
    """
    Parse Tao Te Ching chapters from Gutenberg plain text.

    Strategy: find all chapter-start markers using regex, then collect text
    between them. Chapter starts look like:
      "Ch. 1. 1. The Tao..."  →  Chapter 1
      "2. 1. All in..."       →  Chapter 2
      "6."                    →  Chapter 6 (no inline text)

    We split the body on these markers and pair each chapter number with its text.
    """
    skip_kws = {"gutenberg", "transcriber", "produced by", "ebook", "www.gutenberg"}

    # Find chapter boundaries: lines that are "Ch. N." or "N. 1." where N is a chapter number.
    # Match the start of a chapter: optional "Ch. " then a digit, a period, optional space,
    # then either another digit (verse number) or end-of-line (bare chapter heading).
    chap_re = re.compile(
        r"(?:^|\n)(?:Ch\.\s*)?(\d{1,2})\.\s*(?=\d+\.\s|\s*$|\s+[A-Z\"])",
        re.MULTILINE,
    )

    parts  = chap_re.split(body)
    # After split: [pre_text, chap_num_str, text1, chap_num_str2, text2, ...]

    chapters: list[tuple[int, str]] = []
    i = 1  # skip preamble
    while i < len(parts) - 1:
        try:
            chap_num = int(parts[i])
        except ValueError:
            i += 2
            continue

        raw_text = parts[i + 1]
        # Clean the text
        lines = []
        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            if any(kw in lower for kw in skip_kws):
                continue
            # Skip sub-verse number lines like "2." "3." etc.
            if re.match(r"^\d+\.\s*$", stripped):
                continue
            lines.append(stripped)

        text = clean_ws(" ".join(lines))
        if len(text) > 15 and 1 <= chap_num <= 81:
            chapters.append((chap_num, text))

        i += 2

    return chapters


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
    chapters = parse_ttc_chapters(body)

    if not chapters:
        logger.warning("No chapters parsed for %s", cfg["name"])
        return 0

    logger.info("  %s: %d chapters parsed", cfg["name"], len(chapters))

    verses = [
        {
            "religion":    RELIGION,
            "text":        text,
            "translation": cfg["translation"],
            "book":        cfg["book"],
            "chapter":     chap,
            "verse":       1,
            "reference":   f"{cfg['ref_prefix']} {chap}",
            "source_url":  cfg["url"],
        }
        for chap, text in chapters
    ]

    total = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch      = verses[i : i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(
                id=stable_id(cfg["id_prefix"], v["chapter"]),
                vector=emb,
                payload=v,
            )
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)

    logger.info("  %s: %d chapters ingested", cfg["name"], total)
    return total


async def ingest_taoism():
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

    logger.info("Taoism ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_taoism())
