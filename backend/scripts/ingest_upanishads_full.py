"""
Ingest principal Upanishads from Project Gutenberg (Public Domain).
Source: The Upanishads translated by Swami Paramananda (PG #3283)
Contains: Isa Upanishad, Katha Upanishad, Kena Upanishad
Parses Roman-numeral verse structure from the plain-text file.
Generates deterministic IDs so re-running is safe (upsert = no duplicates).
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

RELIGION    = "Hinduism"
TRANSLATION = "The Upanishads, tr. Swami Paramananda (Project Gutenberg #3283, Public Domain)"
BATCH_SIZE  = 20

GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/3283/pg3283.txt"

# Roman numeral → integer mapping (up to 50)
_ROMAN = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8,
    'IX': 9, 'X': 10, 'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15,
    'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19, 'XX': 20, 'XXI': 21,
    'XXII': 22, 'XXIII': 23, 'XXIV': 24, 'XXV': 25, 'XXVI': 26, 'XXVII': 27,
    'XXVIII': 28, 'XXIX': 29, 'XXX': 30, 'XXXI': 31, 'XXXII': 32,
    'XXXIII': 33, 'XXXIV': 34, 'XXXV': 35, 'XL': 40, 'XLV': 45, 'L': 50,
}
ROMAN_RE = re.compile(r'^(X{0,3})(IX|IV|V?I{0,3})$')

def is_roman(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    return bool(ROMAN_RE.match(s)) and s in _ROMAN


def roman_to_int(s: str) -> int:
    return _ROMAN.get(s.strip(), 0)


# Section header patterns (as they appear in Gutenberg text)
UPANISHAD_HEADERS = [
    ("Isa Upanishad",   re.compile(r'Isa-Upanishad', re.IGNORECASE)),
    ("Katha Upanishad", re.compile(r'Katha-Upanishad', re.IGNORECASE)),
    ("Kena Upanishad",  re.compile(r'Kena-Upanishad', re.IGNORECASE)),
]

# Sub-section markers for Katha (chapters/vallis)
KATHA_CHAPTERS = re.compile(
    r'(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH)\s+VALLI', re.IGNORECASE
)


def parse_upanishads(text: str) -> list[dict]:
    """
    Split the Gutenberg plain-text file into paragraph blocks and extract
    verses by detecting Roman-numeral headings that immediately precede a
    paragraph of scripture text.

    Returns a list of dicts ready for ingestion.
    """
    # Strip Gutenberg header/footer
    start = text.find("*** START OF THE PROJECT GUTENBERG EBOOK")
    end   = text.find("*** END OF THE PROJECT GUTENBERG EBOOK")
    if start != -1:
        text = text[start:]
    if end != -1:
        text = text[:end]

    lines = text.splitlines()
    # Collapse runs of blank lines → single blank
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.strip() == "":
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
        else:
            current.append(line.strip())
    if current:
        paragraphs.append(" ".join(current).strip())

    # Identify which paragraph each Upanishad section starts at.
    # Skip the TOC by taking the LAST standalone match for each section,
    # so that the in-text header (not the table of contents) is used.
    section_starts: list[tuple[int, str]] = []  # (para_idx, upanishad_name)
    for name, pattern in UPANISHAD_HEADERS:
        # Collect all matching short paragraphs
        candidates = [
            i for i, para in enumerate(paragraphs)
            if pattern.search(para) and len(para) < 60
        ]
        if candidates:
            # Use the last occurrence (actual section, not TOC)
            section_starts.append((candidates[-1], name))

    section_starts.sort(key=lambda x: x[0])

    verses: list[dict] = []

    for sec_idx, (sec_start, upanishad_name) in enumerate(section_starts):
        sec_end = section_starts[sec_idx + 1][0] if sec_idx + 1 < len(section_starts) else len(paragraphs)
        sec_paras = paragraphs[sec_start:sec_end]

        # For multi-chapter texts like Katha, track chapter/valli
        chapter_num = 1
        chapter_label = "Valli 1"

        # Scan for Roman numerals and take the NEXT paragraph as the verse
        i = 0
        while i < len(sec_paras):
            para = sec_paras[i]

            # Detect chapter boundary for Katha
            m = KATHA_CHAPTERS.search(para)
            if m:
                words = ["FIRST","SECOND","THIRD","FOURTH","FIFTH","SIXTH"]
                for n, w in enumerate(words, 1):
                    if w.upper() in para.upper():
                        chapter_num = n
                        chapter_label = f"Valli {n}"
                        break
                i += 1
                continue

            if is_roman(para) and i + 1 < len(sec_paras):
                verse_num = roman_to_int(para)
                verse_text = sec_paras[i + 1].strip()

                # Skip if it looks like navigation/header text or too short
                if (len(verse_text) >= 40
                        and not verse_text.lower().startswith("peace chant")
                        and "project gutenberg" not in verse_text.lower()
                        and "here ends" not in verse_text.lower()):

                    chapter_for_ref = chapter_label if upanishad_name == "Katha Upanishad" else "Chapter 1"
                    reference = f"{upanishad_name} {chapter_for_ref}:{verse_num}"

                    verses.append({
                        "religion":    RELIGION,
                        "text":        verse_text,
                        "translation": TRANSLATION,
                        "book":        upanishad_name,
                        "chapter":     chapter_num,
                        "verse":       verse_num,
                        "reference":   reference,
                        "source_url":  GUTENBERG_URL,
                    })
                i += 2  # skip both the Roman numeral and the verse paragraph
            else:
                i += 1

    logger.info("Parsed %d verses from %d Upanishads", len(verses), len(section_starts))
    return verses


def stable_id(upanishad: str, chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Hinduism:Upanishad:{upanishad}:{chapter}:{verse}"))


async def ingest_upanishads_full():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    logger.info("Downloading Upanishads from Project Gutenberg …")
    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}, timeout=30) as http:
        r = await http.get(GUTENBERG_URL)
        if r.status_code != 200:
            logger.error("Failed to download text: HTTP %d", r.status_code)
            return
        raw_text = r.text

    all_verses = parse_upanishads(raw_text)

    if not all_verses:
        logger.error("No verses parsed — check text format.")
        return

    logger.info("Total verses to ingest: %d", len(all_verses))

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
        logger.info("Upserted %d / %d", total, len(all_verses))

    logger.info("Upanishads ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_upanishads_full())
