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
        "url_fallback": "https://gutenberg.pglaf.org/2/1/6/216/216-0.txt",
        "name":        "Tao Te Ching (James Legge)",
        "id_prefix":   "TTC_Legge",
        "translation": "Tao Te Ching (James Legge, Public Domain)",
        "book":        "Tao Te Ching",
        "ref_prefix":  "Tao Te Ching",
    },
    {
        "url":         "https://www.gutenberg.org/cache/epub/7005/pg7005.txt",
        "url_fallback": "https://gutenberg.pglaf.org/7/0/0/7005/7005-0.txt",
        "name":        "Tao Te Ching (Suzuki & Carus)",
        "id_prefix":   "TTC_Carus",
        "translation": "Tao Te Ching (Suzuki & Carus, Public Domain)",
        "book":        "Tao Te Ching",
        "ref_prefix":  "Tao Te Ching",
    },
    {
        "url":         "https://gutenberg.pglaf.org/5/9/7/0/59709/59709-0.txt",
        "name":        "Chuang Tzu (Herbert Giles)",
        "id_prefix":   "ZhuangziGiles",
        "translation": "Chuang Tzu: Mystic, Moralist, and Social Reformer (Herbert Giles, Public Domain)",
        "book":        "Zhuangzi",
        "ref_prefix":  "Zhuangzi",
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


def parse_zhuangzi_chapters(body: str, max_words: int = 200) -> list[tuple[int, int, str]]:
    """
    Parse Zhuangzi (Chuang Tzu) chapters from Gutenberg plain text.
    Chapters are headed by 'CHAPTER I.', 'CHAPTER II.', etc.
    Each chapter is split into ~200-word chunks.
    Returns list of (chapter_num, chunk_idx, text).
    """
    skip_kws = {"gutenberg", "transcriber", "produced by", "ebook", "www.gutenberg"}

    roman = {
        "I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,"VII":7,"VIII":8,"IX":9,"X":10,
        "XI":11,"XII":12,"XIII":13,"XIV":14,"XV":15,"XVI":16,"XVII":17,"XVIII":18,
        "XIX":19,"XX":20,"XXI":21,"XXII":22,"XXIII":23,"XXIV":24,"XXV":25,
        "XXVI":26,"XXVII":27,"XXVIII":28,"XXIX":29,"XXX":30,"XXXI":31,"XXXII":32,"XXXIII":33,
    }

    chap_re = re.compile(r"^CHAPTER\s+([IVXLC]+)\.\s*$", re.MULTILINE)
    parts   = chap_re.split(body)

    results: list[tuple[int, int, str]] = []

    for idx in range(1, len(parts), 2):
        roman_str  = parts[idx].strip()
        chap_num   = roman.get(roman_str, 0)
        if not chap_num:
            continue
        raw_text = parts[idx + 1] if idx + 1 < len(parts) else ""

        lines = []
        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            if any(kw in lower for kw in skip_kws):
                continue
            lines.append(stripped)

        # Word-cap chunking within each chapter
        buf_words: list[str] = []
        buf_parts: list[str] = []
        chunk_idx = 0

        def flush_chunk():
            nonlocal chunk_idx
            if buf_parts:
                text = clean_ws(" ".join(buf_parts))
                if len(text.split()) >= 8:
                    results.append((chap_num, chunk_idx, text))
                    chunk_idx += 1
                buf_words.clear()
                buf_parts.clear()

        for line in lines:
            words = line.split()
            if len(buf_words) + len(words) > max_words and buf_words:
                flush_chunk()
            buf_words.extend(words)
            buf_parts.append(line)

        flush_chunk()

    return results


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
    if not raw and cfg.get("url_fallback"):
        raw = await fetch_text(http, sem, cfg["url_fallback"])
    if not raw:
        logger.error("Could not fetch %s", cfg["name"])
        return 0

    body = extract_gutenberg_body(raw)

    # Dispatch parser based on text type
    is_zhuangzi = "ZhuangziGiles" in cfg.get("id_prefix", "")

    if is_zhuangzi:
        zchunks = parse_zhuangzi_chapters(body)
        if not zchunks:
            logger.warning("No chapters parsed for %s", cfg["name"])
            return 0
        logger.info("  %s: %d chunks parsed", cfg["name"], len(zchunks))
        verses = [
            {
                "religion":    RELIGION,
                "text":        text,
                "translation": cfg["translation"],
                "book":        cfg["book"],
                "chapter":     chap_num,
                "verse":       chunk_idx + 1,
                "reference":   f"{cfg['ref_prefix']} {chap_num}",
                "source_url":  cfg["url"],
            }
            for chap_num, chunk_idx, text in zchunks
        ]
        total = 0
        for i in range(0, len(verses), BATCH_SIZE):
            batch = verses[i : i + BATCH_SIZE]
            embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
            points = [
                PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_DNS,
                           f"Taoism:{cfg['id_prefix']}:{v['chapter']}:{v['verse']}")),
                    vector=emb,
                    payload=v,
                )
                for v, emb in zip(batch, embeddings)
            ]
            client_q.upsert(collection_name=settings.qdrant_collection, points=points)
            total += len(points)
        logger.info("  %s: %d chunks ingested", cfg["name"], total)
        return total

    # TTC parsing path
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
