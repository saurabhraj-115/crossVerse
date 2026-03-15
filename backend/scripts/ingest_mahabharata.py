"""
Ingest Mahabharata (Ganguli translation) from aasi-archive/mbh GitHub repo.
Source: https://github.com/aasi-archive/mbh — 18 parva TXT files (Public Domain).
Translation: Kisari Mohan Ganguli (~1883–1896).
Chunks text by Section, then into ~200-word passages.
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
TRANSLATION = "Mahabharata (tr. Kisari Mohan Ganguli, 1883–1896, Public Domain)"
BATCH_SIZE  = 20
CONCURRENCY = 4
CHUNK_WORDS = 200

GITHUB_API = "https://api.github.com/repos/aasi-archive/mbh/contents"
GITHUB_RAW = "https://raw.githubusercontent.com/aasi-archive/mbh/main"

# Canonical parva order with display names
PARVA_ORDER = [
    "adi", "sabha", "vana", "virata", "udyoga",
    "bhishma", "drona", "karna", "shalya", "sauptika",
    "stri", "shanti", "anushasana", "ashvamedhika",
    "ashramavasika", "mausala", "mahaprasthanika", "svargarohanika",
]

PARVA_DISPLAY = {
    "adi":              "Adi Parva (Book of the Beginning)",
    "sabha":            "Sabha Parva (Book of the Assembly Hall)",
    "vana":             "Vana Parva (Book of the Forest)",
    "virata":           "Virata Parva (Book of Virata)",
    "udyoga":           "Udyoga Parva (Book of the Effort)",
    "bhishma":          "Bhishma Parva (Book of Bhishma)",
    "drona":            "Drona Parva (Book of Drona)",
    "karna":            "Karna Parva (Book of Karna)",
    "shalya":           "Shalya Parva (Book of Shalya)",
    "sauptika":         "Sauptika Parva (Book of the Sleeping Warriors)",
    "stri":             "Stri Parva (Book of the Women)",
    "shanti":           "Shanti Parva (Book of Peace)",
    "anushasana":       "Anushasana Parva (Book of Instructions)",
    "ashvamedhika":     "Ashvamedhika Parva (Book of the Horse Sacrifice)",
    "ashramavasika":    "Ashramavasika Parva (Book of the Hermitage)",
    "mausala":          "Mausala Parva (Book of the Clubs)",
    "mahaprasthanika":  "Mahaprasthanika Parva (Book of the Great Journey)",
    "svargarohanika":   "Svargarohanika Parva (Book of the Ascent to Heaven)",
}


def stable_id(parva: str, section: int, chunk: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS,
        f"Hinduism:Mahabharata:{parva}:{section}:{chunk}"))


def _normalize_parva_key(filename: str) -> str | None:
    """Map a filename to a canonical parva key."""
    fn = filename.lower().replace("-", "_").replace(" ", "_")
    # Strip extension
    fn = re.sub(r"\.(txt|md)$", "", fn)
    for key in PARVA_ORDER:
        if key in fn:
            return key
    return None


def split_into_chunks(text: str, target_words: int = CHUNK_WORDS) -> list[str]:
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
    return [c for c in chunks if len(c.split()) >= 30]


def parse_parva_text(raw: str, parva_key: str) -> list[dict]:
    """
    Parse a Ganguli-translation parva TXT file.
    The Ganguli text uses 'SECTION N' or 'Section N' headings.
    Text inside each section is chunked into ~200-word passages.
    """
    parva_name = PARVA_DISPLAY.get(parva_key, parva_key.title() + " Parva")

    # Clean boilerplate lines
    raw = re.sub(r"Sacred Texts[^\n]*\n", "", raw)
    raw = re.sub(r"Mahabharata[^\n]*Index[^\n]*\n", "", raw)

    # Split on SECTION markers
    section_re = re.compile(r'SECTION\s+([IVXLCDM]+|\d+)', re.IGNORECASE)
    parts = section_re.split(raw)
    # parts = [preamble, sec_id, sec_body, sec_id, sec_body, ...]

    # Roman numeral → int
    def roman(s: str) -> int:
        vals = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
        try:
            n = int(s)
            return n
        except ValueError:
            pass
        result, prev = 0, 0
        for ch in reversed(s.upper()):
            v = vals.get(ch, 0)
            result += v if v >= prev else -v
            prev = v
        return result

    verses: list[dict] = []
    i = 1
    while i < len(parts) - 1:
        sec_label = parts[i].strip()
        sec_body  = parts[i + 1]
        sec_num   = roman(sec_label) or 0
        i += 2

        if not sec_num:
            continue

        chunks = split_into_chunks(sec_body)
        for chunk_idx, chunk_text in enumerate(chunks, start=1):
            verses.append({
                "religion":    RELIGION,
                "text":        chunk_text,
                "translation": TRANSLATION,
                "book":        parva_name,
                "chapter":     sec_num,
                "verse":       chunk_idx,
                "reference":   f"Mahabharata, {parva_name}, Section {sec_label}, Part {chunk_idx}",
                "source_url":  f"https://github.com/aasi-archive/mbh",
            })

    return verses


async def fetch_file_list(http: httpx.AsyncClient) -> list[tuple[str, str]]:
    """
    Returns list of (parva_key, raw_url) for all TXT files in the repo.
    Falls back to hardcoded list if API call fails.
    """
    try:
        r = await http.get(GITHUB_API, timeout=15,
                           headers={"Accept": "application/vnd.github+json"})
        if r.status_code == 200:
            items = r.json()
            files = []
            for item in items:
                name = item.get("name", "")
                if not name.lower().endswith(".txt"):
                    continue
                key = _normalize_parva_key(name)
                if key:
                    files.append((key, item["download_url"]))
            if files:
                logger.info("GitHub API: found %d parva TXT files", len(files))
                return files
    except Exception as exc:
        logger.warning("GitHub API failed: %s — trying fallback URLs", exc)

    # Fallback: try common naming conventions
    fallback_patterns = [
        # pattern: txt/maha{N:02d}.txt  (aasi-archive/mbh actual layout)
        [(k, f"{GITHUB_RAW}/txt/maha{i+1:02d}.txt") for i, k in enumerate(PARVA_ORDER)],
        # pattern: {key}_parva.txt
        [(k, f"{GITHUB_RAW}/{k}_parva.txt") for k in PARVA_ORDER],
        # pattern: {N:02d}_{key}.txt
        [(k, f"{GITHUB_RAW}/{i+1:02d}_{k}.txt") for i, k in enumerate(PARVA_ORDER)],
        # pattern: {key}.txt
        [(k, f"{GITHUB_RAW}/{k}.txt") for k in PARVA_ORDER],
    ]
    # Return first pattern set (will be probed at fetch time)
    return fallback_patterns[0]


async def fetch_parva(
    http: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    parva_key: str,
    url: str,
) -> list[dict]:
    async with sem:
        for attempt in range(3):
            try:
                r = await http.get(url, timeout=60)
                if r.status_code == 200:
                    logger.info("  ✓ %s (%d bytes)", parva_key, len(r.content))
                    return parse_parva_text(r.text, parva_key)
                elif r.status_code == 404:
                    logger.warning("  404: %s → %s", parva_key, url)
                    return []
            except Exception as exc:
                if attempt == 2:
                    logger.warning("  Failed %s: %s", parva_key, exc)
                await asyncio.sleep(2 ** attempt)
    return []


async def ingest_mahabharata():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem = asyncio.Semaphore(CONCURRENCY)

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 CrossVerse/1.0"},
        follow_redirects=True,
    ) as http:
        file_list = await fetch_file_list(http)

        tasks = [fetch_parva(http, sem, key, url) for key, url in file_list]
        results = await asyncio.gather(*tasks)

    all_verses = [v for parva_verses in results for v in parva_verses]
    logger.info("Total Mahabharata chunks: %d", len(all_verses))

    if not all_verses:
        logger.error("No content fetched. Check repo name / file structure.")
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
        if total % 500 == 0 or total == len(all_verses):
            logger.info("Upserted %d / %d", total, len(all_verses))

    logger.info("Mahabharata ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_mahabharata())
