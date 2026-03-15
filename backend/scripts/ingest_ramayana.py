"""
Ingest Valmiki Ramayana (Griffith translation) from PDF.
Source: www.hariomgroup.org — Griffith's verse translation (1870-74, Public Domain)
Splits each canto into ~150-word chunks for optimal RAG retrieval.
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

RELIGION    = "Hinduism"
TRANSLATION = "Valmiki Ramayana (tr. Ralph T.H. Griffith, 1870-74, Public Domain)"
BATCH_SIZE  = 20
CHUNK_WORDS = 150   # target words per chunk
PDF_URL     = "https://www.hariomgroup.org/hariombooks_shastra/Ramayana/Valmiki-Ramayana-Eng-Translation-Griffith.pdf"

BOOK_NAMES = {
    "BOOK I.":   "Bala Kanda",
    "BOOK II.":  "Ayodhya Kanda",
    "BOOK III.": "Aranya Kanda",
    "BOOK IV.":  "Kishkindha Kanda",
    "BOOK V.":   "Sundara Kanda",
    "BOOK VI.":  "Yuddha Kanda",
}

ROMAN_TO_INT = {}
def _build_roman_map():
    vals = [1000,900,500,400,100,90,50,40,10,9,5,4,1]
    syms = ["M","CM","D","CD","C","XC","L","XL","X","IX","V","IV","I"]
    for n in range(1, 200):
        result, num = "", n
        for v, s in zip(vals, syms):
            while num >= v:
                result += s
                num -= v
        ROMAN_TO_INT[result] = n

_build_roman_map()


def clean_text(raw: str) -> str:
    """Strip PDF navigation noise, page markers, and footnote refs."""
    t = re.sub(r"Sacred Texts[^\n]*\n", "", raw)
    t = re.sub(r"Hinduism[^\n]*\n", "", t)
    t = re.sub(r"\np\. \d+[a-z]?\n", "\n", t)
    t = re.sub(r" \d+[ab]?[\.,](?=\s|\n)", "", t)   # footnote refs like "1b,"
    t = re.sub(r"\*+", "", t)
    t = re.sub(r"\[illegible\]", "", t, flags=re.IGNORECASE)
    t = re.sub(r"[ \t]+", " ", t)
    return t


def split_into_chunks(text: str, target_words: int = CHUNK_WORDS) -> list[str]:
    """Split a long canto text into ~target_words-word chunks at sentence/line boundaries."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    chunks, current, count = [], [], 0
    for line in lines:
        words = len(line.split())
        current.append(line)
        count += words
        if count >= target_words:
            chunks.append(" ".join(current))
            current, count = [], 0
    if current:
        chunks.append(" ".join(current))
    return [c for c in chunks if len(c.split()) >= 20]


def parse_pdf(raw_text: str) -> list[dict]:
    """
    Parse full PDF text into verse chunks keyed by (book, canto, chunk_idx).
    """
    text = clean_text(raw_text)

    # Split into BOOK sections
    book_pattern = re.compile(r"(BOOK [IVX]+\.)(.*?)(?=BOOK [IVX]+\.|$)", re.DOTALL)
    book_matches = list(book_pattern.finditer(text))

    # Canto pattern within each book section
    canto_pattern = re.compile(
        r"CANTO ([IVX]+)[:\.]([^\n]*)\n(.*?)(?=CANTO [IVX]+[:\.]|$)",
        re.DOTALL,
    )

    verses: list[dict] = []

    for bm in book_matches:
        book_key = bm.group(1).strip()
        book_name = BOOK_NAMES.get(book_key, book_key)
        book_text = bm.group(2)

        for cm in canto_pattern.finditer(book_text):
            canto_roman = cm.group(1).strip()
            canto_title = cm.group(2).strip().rstrip(".")
            canto_body  = cm.group(3)

            canto_num = ROMAN_TO_INT.get(canto_roman, 0)
            if not canto_num:
                continue

            chunks = split_into_chunks(canto_body)
            for chunk_idx, chunk_text in enumerate(chunks, start=1):
                verses.append({
                    "religion":    RELIGION,
                    "text":        chunk_text,
                    "translation": TRANSLATION,
                    "book":        f"Ramayana – {book_name}",
                    "chapter":     canto_num,
                    "verse":       chunk_idx,
                    "reference":   f"Ramayana {book_name}, Canto {canto_roman} ({canto_title}), Part {chunk_idx}",
                    "source_url":  PDF_URL,
                })

    return verses


def stable_id(book: str, canto: int, chunk: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Hinduism:Ramayana:{book}:{canto}:{chunk}"))


async def ingest_ramayana():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    logger.info("Downloading Ramayana PDF …")
    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}, timeout=120) as http:
        r = await http.get(PDF_URL)
        if r.status_code != 200:
            logger.error("Download failed: HTTP %d", r.status_code)
            return
        pdf_bytes = r.content

    logger.info("PDF downloaded (%d MB). Extracting text …", len(pdf_bytes) // 1_000_000)

    try:
        import pypdf, io
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        raw_text = ""
        for page in reader.pages:
            raw_text += page.extract_text() + "\n"
    except Exception as exc:
        logger.error("PDF extraction failed: %s", exc)
        return

    logger.info("Parsing %d chars of text …", len(raw_text))
    all_verses = parse_pdf(raw_text)
    logger.info("Total chunks to ingest: %d", len(all_verses))

    if not all_verses:
        logger.error("No verses parsed.")
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

    logger.info("Ramayana ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_ramayana())
