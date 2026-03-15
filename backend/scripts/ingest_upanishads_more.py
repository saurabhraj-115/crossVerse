"""
Ingest remaining principal Upanishads (beyond Isa, Katha, Kena already ingested).
Sources:
  - Archive.org SBE Vol 1  → Chandogya, Aitareya, Kaushitaki
  - Archive.org SBE Vol 15 → Mundaka, Taittiriya, Brihadaranyaka, Svetasvatara, Prashna, Maitrayani
Translation: Max Müller, Sacred Books of the East (Public Domain).
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
CHUNK_WORDS = 120  # Upanishads have dense prose; smaller chunks work better

# -------------------------------------------------------------------
# Sources to fetch
# -------------------------------------------------------------------
_SBE = "https://archive.org/download/the-sacred-books-of-the-east-complete-50-volumes"

SOURCES = [
    {
        # SBE Vol 1: Khandogya (Chandogya), Aitareya-Aranyaka, Kaushitaki
        # (Talavakara/Kena and Vagasaneyi/Isa are already ingested — skipped by ALREADY_INGESTED)
        "url": f"{_SBE}/the-sacred-books-of-the-east-01_djvu.txt",
        "translation": "The Upanishads Part I, tr. F. Max Müller (SBE Vol 1, Public Domain)",
        "targets": ["Chandogya", "Aitareya", "Kaushitaki"],
    },
    {
        # SBE Vol 15: Mundaka, Taittiriya, Brihadaranyaka, Svetasvatara, Prashna, Maitrayani
        # (Katha is already ingested — skipped by ALREADY_INGESTED)
        "url": f"{_SBE}/the-sacred-books-of-the-east-15_djvu.txt",
        "translation": "The Upanishads Part II, tr. F. Max Müller (SBE Vol 15, Public Domain)",
        "targets": ["Mundaka", "Taittiriya", "Brihadaranyaka", "Svetasvatara", "Maitrayani", "Prashna"],
    },
]

# Note: Mandukya (12 mantras) is not in these volumes and can be added separately.
EXTRA_SOURCES: list[dict] = []

# Skip these — already ingested by ingest_upanishads_full.py
# Include OCR variant names used in the Archive.org DjVuTXT files
ALREADY_INGESTED = {"Isa", "Katha", "Kena", "Vagasaneyi", "Talavakara"}

# Section headers in the Archive.org OCR text (DjVuTXT).
# Vol 1 uses: KHANDOGYA-UPANISHAD, AITAREYA-ARANYAKA, KAUSHITAKI-BRAHMANA-UPANISHAD
# Vol 15 uses: MUNDAKA-, TAITTIRIYAKA-, BRIHADARANYAKA-, SVETASVATARA-, PRASNA-, MAITRÁYANA-
UPANISHAD_SECTION_RE = re.compile(
    r'(KHANDOGYA|CHANDOGYA|AITAREYA|KAUSHITAKI|MUNDAKA|TAITTIRIYAKA?|BRIHADARANYAKA|'
    r'SVETASVATARA|MAITRA[YÁ][AÁ]N[AI]|MANDUKYA|PRA[SŚ]NA)',
    re.IGNORECASE,
)

# Verse number patterns in these texts: "1.", "1. 1.", "I, 1.", etc.
VERSE_NUM_RE = re.compile(r'^\d[\d,\.\s]*$')


def stable_id(upanishad: str, chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS,
        f"Hinduism:Upanishad:{upanishad}:{chapter}:{verse}"))


def strip_gutenberg_header_footer(text: str) -> str:
    start = text.find("*** START OF THE PROJECT GUTENBERG EBOOK")
    end   = text.find("*** END OF THE PROJECT GUTENBERG EBOOK")
    if start != -1:
        text = text[start + 60:]
    if end != -1:
        text = text[:end]
    return text


def to_paragraphs(text: str) -> list[str]:
    """Collapse multi-blank lines → paragraphs."""
    lines = text.splitlines()
    paragraphs, current = [], []
    for line in lines:
        s = line.strip()
        if s == "":
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
        else:
            current.append(s)
    if current:
        paragraphs.append(" ".join(current).strip())
    return paragraphs


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


def parse_gutenberg_upanishads(text: str, targets: list[str], translation: str) -> list[dict]:
    """
    Parse a multi-Upanishad Gutenberg file.
    Identifies section boundaries by Upanishad title headers.
    Within each section, chunks text into ~CHUNK_WORDS passages.
    """
    text = strip_gutenberg_header_footer(text)
    paras = to_paragraphs(text)

    # Find where each target Upanishad starts
    section_starts: list[tuple[int, str]] = []
    for i, para in enumerate(paras):
        m = UPANISHAD_SECTION_RE.search(para)
        if m and len(para) < 80:  # short header paragraph
            name_raw = m.group(1).title()
            # Map to canonical name
            canonical = _canonical_name(name_raw)
            if canonical in targets and canonical not in ALREADY_INGESTED:
                # Use last occurrence (skip TOC)
                section_starts = [s for s in section_starts if s[1] != canonical]
                section_starts.append((i, canonical))

    section_starts.sort(key=lambda x: x[0])
    logger.info("Found sections: %s", [s[1] for s in section_starts])

    # Chapter header patterns (Prapathaka, Adhyaya, Brahman, Mundaka, Valli, etc.)
    chapter_re = re.compile(
        r'(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|'
        r'ELEVENTH|TWELFTH|THIRTEENTH|FOURTEENTH|FIFTEENTH|'
        r'\d+(?:ST|ND|RD|TH)?)\s+'
        r'(PRAPATHAKA|ADHYAYA|BRAHMAN[A]?|MUNDAKA|VALLI|CHAPTER|PRASNA|ANUVAKA)',
        re.IGNORECASE,
    )
    ordinal_map = {
        "FIRST":1,"SECOND":2,"THIRD":3,"FOURTH":4,"FIFTH":5,"SIXTH":6,
        "SEVENTH":7,"EIGHTH":8,"NINTH":9,"TENTH":10,"ELEVENTH":11,
        "TWELFTH":12,"THIRTEENTH":13,"FOURTEENTH":14,"FIFTEENTH":15,
    }

    verses: list[dict] = []

    for si, (sec_start, upanishad_name) in enumerate(section_starts):
        sec_end = section_starts[si + 1][0] if si + 1 < len(section_starts) else len(paras)
        sec_paras = paras[sec_start:sec_end]

        chapter_num = 1
        chunk_idx   = 0
        buffer: list[str] = []

        def flush_buffer():
            nonlocal chunk_idx
            if not buffer:
                return
            text_block = " ".join(buffer).strip()
            for chunk in split_into_chunks(text_block):
                chunk_idx += 1
                verses.append({
                    "religion":    RELIGION,
                    "text":        chunk,
                    "translation": translation,
                    "book":        f"{upanishad_name} Upanishad",
                    "chapter":     chapter_num,
                    "verse":       chunk_idx,
                    "reference":   f"{upanishad_name} Upanishad {chapter_num}.{chunk_idx}",
                    "source_url":  "https://www.gutenberg.org",
                })
            buffer.clear()

        for para in sec_paras:
            m = chapter_re.search(para)
            if m and len(para) < 80:
                flush_buffer()
                ord_word = m.group(1).upper()
                if ord_word in ordinal_map:
                    chapter_num = ordinal_map[ord_word]
                else:
                    try:
                        chapter_num = int(re.sub(r'\D', '', ord_word)) or chapter_num + 1
                    except ValueError:
                        chapter_num += 1
                chunk_idx = 0
                continue

            if len(para) >= 40:
                buffer.append(para)
                if sum(len(p.split()) for p in buffer) >= CHUNK_WORDS:
                    flush_buffer()

        flush_buffer()
        logger.info("  %s Upanishad: %d chunks", upanishad_name, chunk_idx)

    return verses


def _canonical_name(raw: str) -> str:
    # Maps OCR name variants (from Archive.org DjVuTXT) to canonical names
    mapping = {
        "Khandogya":    "Chandogya",   # Vol 1 OCR spelling
        "Chandogya":    "Chandogya",
        "Aitareya":     "Aitareya",
        "Kaushitaki":   "Kaushitaki",
        "Mundaka":      "Mundaka",
        "Taittiriyaka": "Taittiriya",  # Vol 15 OCR spelling
        "Taittiriya":   "Taittiriya",
        "Brihadaranyaka": "Brihadaranyaka",
        "Svetasvatara": "Svetasvatara",
        "Maitrayana":   "Maitrayani",  # Vol 15 OCR spelling
        "Maitrayani":   "Maitrayani",
        "Mandukya":     "Mandukya",
        "Prasna":       "Prashna",     # Vol 15 OCR spelling
        "Prashna":      "Prashna",
    }
    for k, v in mapping.items():
        if k.lower() in raw.lower():
            return v
    return raw.title()


def parse_sacred_texts_html(html: str, name: str, translation: str) -> list[dict]:
    """Simple parser for sacred-texts.com HTML pages (strips tags, extracts paragraphs)."""
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&#\d+;', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # Split into sentences as pseudo-verses
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip().split()) >= 10]

    verses = []
    buffer, chapter_num, chunk_idx = [], 1, 0
    for sent in sentences:
        buffer.append(sent)
        if sum(len(s.split()) for s in buffer) >= CHUNK_WORDS:
            chunk_idx += 1
            verses.append({
                "religion":    RELIGION,
                "text":        " ".join(buffer),
                "translation": translation,
                "book":        f"{name}",
                "chapter":     chapter_num,
                "verse":       chunk_idx,
                "reference":   f"{name} Part {chunk_idx}",
                "source_url":  "https://www.sacred-texts.com",
            })
            buffer = []
    if buffer:
        chunk_idx += 1
        verses.append({
            "religion":    RELIGION,
            "text":        " ".join(buffer),
            "translation": translation,
            "book":        name,
            "chapter":     chapter_num,
            "verse":       chunk_idx,
            "reference":   f"{name} Part {chunk_idx}",
            "source_url":  "https://www.sacred-texts.com",
        })
    return verses


async def fetch_source(http: httpx.AsyncClient, url: str) -> str:
    for attempt in range(3):
        try:
            r = await http.get(url, timeout=60)
            if r.status_code == 200:
                return r.text
            logger.warning("HTTP %d for %s", r.status_code, url)
        except Exception as exc:
            if attempt == 2:
                logger.error("Failed %s: %s", url, exc)
            await asyncio.sleep(2 ** attempt)
    return ""


async def ingest_upanishads_more():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    all_verses: list[dict] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 CrossVerse/1.0"},
        follow_redirects=True,
    ) as http:
        # Fetch Gutenberg multi-Upanishad files
        for src in SOURCES:
            logger.info("Downloading %s …", src["url"])
            text = await fetch_source(http, src["url"])
            if text:
                verses = parse_gutenberg_upanishads(text, src["targets"], src["translation"])
                logger.info("  → %d chunks", len(verses))
                all_verses.extend(verses)

        # Fetch extra small texts from sacred-texts.com
        for extra in EXTRA_SOURCES:
            logger.info("Downloading %s …", extra["url"])
            html = await fetch_source(http, extra["url"])
            if html:
                verses = parse_sacred_texts_html(html, extra["name"], extra["translation"])
                logger.info("  %s → %d chunks", extra["name"], len(verses))
                all_verses.extend(verses)

    logger.info("Total Upanishad chunks: %d", len(all_verses))
    if not all_verses:
        logger.error("No verses collected.")
        return

    total = 0
    for i in range(0, len(all_verses), BATCH_SIZE):
        batch = all_verses[i: i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(
                id=stable_id(v["book"], v["chapter"], v["verse"]),
                vector=emb,
                payload=v,
            )
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)
        if total % 200 == 0 or total == len(all_verses):
            logger.info("Upserted %d / %d", total, len(all_verses))

    logger.info("Additional Upanishads ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_upanishads_more())
