"""
Ingest the Four Vedas — Griffith translations (Public Domain).
Sources (Project Gutenberg):
  - Rig Veda  (Ralph T.H. Griffith, 1896)  → PG #12403
  - Sama Veda (Ralph T.H. Griffith, 1893)  → PG #8207
  - Atharva Veda (Ralph T.H. Griffith, 1895) → PG #16295
  - Yajur Veda / White Yajurveda (Ralph T.H. Griffith, 1899) → PG #2290

The Rig Veda is ~400,000 words. We chunk each hymn into ≤200-word passages.
Sama/Yajur/Atharva are smaller and similarly chunked.
Deterministic UUIDs → safe to re-run (upsert).
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

RELIGION   = "Hinduism"
BATCH_SIZE = 20
CHUNK_WORDS = 150

VEDAS = [
    {
        "name":        "Rig Veda",
        "book":        "Rig Veda (Rigveda)",
        "translation": "Rig Veda, tr. Ralph T.H. Griffith (1896, Public Domain)",
        "url":         "https://www.gutenberg.org/cache/epub/12403/pg12403.txt",
        # Hymn pattern: "HYMN I." or "HYMN CXXIII."
        "hymn_re":     re.compile(r'HYMN\s+([IVXLCDM]+)\.', re.IGNORECASE),
        # Book/mandala pattern: "BOOK I." or "MANDALA I"
        "book_re":     re.compile(r'(?:BOOK|MANDALA)\s+([IVXLCDM]+)\.?', re.IGNORECASE),
        "chapter_label": "Mandala",
    },
    {
        "name":        "Sama Veda",
        "book":        "Sama Veda (Samaveda)",
        "translation": "Sama Veda, tr. Ralph T.H. Griffith (1893, Public Domain)",
        "url":         "https://www.gutenberg.org/cache/epub/8207/pg8207.txt",
        "hymn_re":     re.compile(r'(?:HYMN|SONG)\s+([IVXLCDM]+|[\d]+)\.?', re.IGNORECASE),
        "book_re":     re.compile(r'(?:BOOK|PART|ARCHIKA)\s+([IVXLCDM]+|[\d]+)\.?', re.IGNORECASE),
        "chapter_label": "Book",
    },
    {
        "name":        "Atharva Veda",
        "book":        "Atharva Veda (Atharvaveda)",
        "translation": "Atharva Veda, tr. Ralph T.H. Griffith (1895, Public Domain)",
        "url":         "https://www.gutenberg.org/cache/epub/16295/pg16295.txt",
        "hymn_re":     re.compile(r'HYMN\s+([IVXLCDM]+|\d+)\.?', re.IGNORECASE),
        "book_re":     re.compile(r'BOOK\s+([IVXLCDM]+|\d+)\.?', re.IGNORECASE),
        "chapter_label": "Book",
    },
    {
        "name":        "Yajur Veda",
        "book":        "Yajur Veda (White Yajurveda)",
        "translation": "Yajur Veda, tr. Ralph T.H. Griffith (1899, Public Domain)",
        "url":         "https://www.gutenberg.org/cache/epub/2290/pg2290.txt",
        "hymn_re":     re.compile(r'(?:HYMN|CHAPTER|ADHYAYA)\s+([IVXLCDM]+|\d+)\.?', re.IGNORECASE),
        "book_re":     re.compile(r'(?:BOOK|KANDA)\s+([IVXLCDM]+|\d+)\.?', re.IGNORECASE),
        "chapter_label": "Chapter",
    },
]


def roman_to_int(s: str) -> int:
    try:
        return int(s)
    except ValueError:
        pass
    vals = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
    result, prev = 0, 0
    for ch in reversed(s.upper()):
        v = vals.get(ch, 0)
        result += v if v >= prev else -v
        prev = v
    return max(result, 0)


def stable_id(veda_name: str, mandala: int, hymn: int, chunk: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS,
        f"Hinduism:{veda_name}:{mandala}:{hymn}:{chunk}"))


def strip_gutenberg(text: str) -> str:
    start = text.find("*** START OF THE PROJECT GUTENBERG EBOOK")
    end   = text.find("*** END OF THE PROJECT GUTENBERG EBOOK")
    if start != -1:
        text = text[text.index('\n', start) + 1:]
    if end != -1:
        text = text[:end]
    return text


def split_into_chunks(text: str, target_words: int = CHUNK_WORDS) -> list[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    chunks, current, count = [], [], 0
    for line in lines:
        w = len(line.split())
        current.append(line)
        count += w
        if count >= target_words:
            chunks.append(" ".join(current))
            current, count = [], 0
    if current:
        chunks.append(" ".join(current))
    return [c for c in chunks if len(c.split()) >= 20]


def parse_veda_text(raw: str, veda: dict) -> list[dict]:
    """
    Parse a Griffith Veda text (Gutenberg).
    Splits into Mandala/Book → Hymn → chunks.
    """
    text = strip_gutenberg(raw)

    # Remove page markers, translator notes
    text = re.sub(r'p\.\s*\d+\n', '\n', text)
    text = re.sub(r'\[Footnote[^\]]*\]', '', text)
    text = re.sub(r'\[p\.\s*\d+\]', '', text)

    veda_name      = veda["name"]
    veda_book      = veda["book"]
    translation    = veda["translation"]
    hymn_re        = veda["hymn_re"]
    book_re        = veda["book_re"]
    chapter_label  = veda["chapter_label"]

    lines = text.splitlines()

    verses: list[dict] = []
    mandala = 1
    hymn_num = 0
    hymn_buffer: list[str] = []

    def flush_hymn():
        if not hymn_buffer or hymn_num == 0:
            return
        full_text = "\n".join(hymn_buffer)
        for chunk_idx, chunk in enumerate(split_into_chunks(full_text), start=1):
            verses.append({
                "religion":    RELIGION,
                "text":        chunk,
                "translation": translation,
                "book":        veda_book,
                "chapter":     mandala,
                "verse":       hymn_num * 100 + chunk_idx,
                "reference":   f"{veda_name} {chapter_label} {mandala}, Hymn {hymn_num}, Part {chunk_idx}",
                "source_url":  veda["url"],
            })
        hymn_buffer.clear()

    for line in lines:
        stripped = line.strip()

        # Detect book / mandala boundary
        bm = book_re.match(stripped)
        if bm and len(stripped) < 50:
            flush_hymn()
            hymn_num = 0
            mandala = roman_to_int(bm.group(1)) or (mandala + 1)
            continue

        # Detect hymn boundary
        hm = hymn_re.match(stripped)
        if hm and len(stripped) < 60:
            flush_hymn()
            hymn_num = roman_to_int(hm.group(1)) or (hymn_num + 1)
            continue

        # Skip short/empty lines that look like headers/noise
        if len(stripped) < 5:
            continue
        if re.match(r'^[A-Z\s,\.]+$', stripped) and len(stripped) < 40:
            continue

        hymn_buffer.append(stripped)

    flush_hymn()
    logger.info("%s: %d chunks (mandalas/books parsed)", veda_name, len(verses))
    return verses


async def fetch_veda(http: httpx.AsyncClient, veda: dict) -> list[dict]:
    url = veda["url"]
    logger.info("Downloading %s from %s …", veda["name"], url)
    for attempt in range(3):
        try:
            r = await http.get(url, timeout=180)
            if r.status_code == 200:
                logger.info("  Downloaded %s (%.1f MB)", veda["name"], len(r.content)/1e6)
                return parse_veda_text(r.text, veda)
            logger.warning("  HTTP %d for %s", r.status_code, url)
        except Exception as exc:
            if attempt == 2:
                logger.error("  Failed %s: %s", veda["name"], exc)
            await asyncio.sleep(3 ** attempt)
    return []


async def ingest_vedas():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    all_verses: list[dict] = []

    # Fetch all 4 Vedas — sequentially to avoid hammering Gutenberg
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 CrossVerse/1.0"},
        follow_redirects=True,
    ) as http:
        for veda in VEDAS:
            verses = await fetch_veda(http, veda)
            all_verses.extend(verses)

    logger.info("Total Vedic chunks: %d", len(all_verses))
    if not all_verses:
        logger.error("No verses collected — check Gutenberg connectivity.")
        return

    total = 0
    for i in range(0, len(all_verses), BATCH_SIZE):
        batch = all_verses[i: i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(
                id=stable_id(v["book"], v["chapter"], v["verse"], 0),
                vector=emb,
                payload=v,
            )
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)
        if total % 500 == 0 or total == len(all_verses):
            logger.info("Upserted %d / %d", total, len(all_verses))

    logger.info("Vedas ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_vedas())
