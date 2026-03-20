"""
Ingest additional Buddhist texts from SuttaCentral sc-data (Bhikkhu Sujato, CC0):
  - Digha Nikaya  (DN 1–34)   ~long suttas, 200-word chunks
  - Sutta Nipata  (Snp)       discovered via GitHub API (nested vagga subdirs)
  - Theragatha    (Thag)      discovered via GitHub API
  - Therigatha    (Thig)      discovered via GitHub API

Plus Mahayana texts from Project Gutenberg:
  - The Diamond Sutra (PG #64623, Price/Wong translation)

Re-running is safe — deterministic UUIDs, upsert only.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import List

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.services.embeddings import embed_texts

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

RELIGION    = "Buddhism"
TRANSLATION = "Bhikkhu Sujato (CC0, SuttaCentral)"
BATCH_SIZE  = 20
MAX_WORDS   = 200

SC_RAW = "https://raw.githubusercontent.com/suttacentral/sc-data/main/sc_bilara_data/translation/en/sujato/sutta"
GH_API = "https://api.github.com/repos/suttacentral/sc-data/contents/sc_bilara_data/translation/en/sujato/sutta"


# ---------------------------------------------------------------------------
# GitHub helpers (same as ingest_pali_canon.py)
# ---------------------------------------------------------------------------

def _gh_headers() -> dict:
    h = {"User-Agent": "CrossVerse-Ingestion"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


async def github_list(client: httpx.AsyncClient, sem: asyncio.Semaphore, path: str) -> List[dict]:
    """List GitHub directory contents, with rate-limit backoff."""
    url = f"{GH_API}/{path}"
    async with sem:
        for attempt in range(6):
            try:
                r = await client.get(url, headers=_gh_headers(), timeout=30)
                if r.status_code == 200:
                    return r.json()
                if r.status_code in (403, 429):
                    reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 3600))
                    wait  = max(reset - time.time() + 5, 30)
                    logger.warning("GitHub rate limited. Sleeping %.0f s…", wait)
                    await asyncio.sleep(wait)
                    continue
                if r.status_code == 404:
                    return []
            except Exception as e:
                logger.warning("github_list attempt %d failed: %s", attempt + 1, e)
                await asyncio.sleep(2 ** attempt)
    return []


async def fetch_raw(client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str) -> dict | None:
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=30)
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 404:
                    return None
            except Exception as e:
                logger.warning("fetch_raw attempt %d: %s — %s", attempt + 1, url, e)
                await asyncio.sleep(2 ** attempt)
    return None


# ---------------------------------------------------------------------------
# Bilara JSON → chunks (same as ingest_pali_canon.py)
# ---------------------------------------------------------------------------

def _sutta_title(data: dict) -> str:
    """Extract sutta name from bilara JSON (key ending in :0.2)."""
    for k, v in data.items():
        if re.search(r":0\.2$", k) and v and len(v.strip()) < 120:
            return v.strip().rstrip(".")
    return ""


def parse_bilara(data: dict, sutta_ref: str, book_name: str, id_prefix: str) -> list[dict]:
    """
    Parse a single bilara translation JSON into word-capped chunks.
    Skips header/title segments (section == 0).
    """
    segments: list[tuple[str, str]] = []
    for k, v in data.items():
        v = (v or "").strip()
        if not v:
            continue
        m = re.match(r"[^:]+:(\d+)\.", k)
        if m and m.group(1) == "0":
            continue   # title/header segment
        if not m:
            continue
        segments.append((k, v))

    if not segments:
        return []

    segments.sort(key=lambda x: x[0])

    sutta_title  = _sutta_title(data)
    display_book = f"{book_name} – {sutta_title}" if sutta_title else book_name

    chunks: list[dict] = []
    buf_words: list[str] = []
    buf_parts: list[str] = []
    chunk_idx = 0

    def flush():
        nonlocal chunk_idx
        if buf_parts:
            text = " ".join(buf_parts)
            if len(text.split()) >= 8:
                chunks.append({
                    "religion":    RELIGION,
                    "text":        text,
                    "translation": TRANSLATION,
                    "book":        display_book,
                    "chapter":     None,
                    "verse":       chunk_idx + 1,
                    "reference":   sutta_ref,
                    "source_url":  f"https://suttacentral.net/{sutta_ref.replace(' ', '').lower()}",
                })
                chunk_idx += 1
            buf_words.clear()
            buf_parts.clear()

    for _, text in segments:
        words = text.split()
        if len(buf_words) + len(words) > MAX_WORDS and buf_words:
            flush()
        buf_words.extend(words)
        buf_parts.append(text)

    flush()

    result = []
    for i, c in enumerate(chunks):
        c["_id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Buddhism:{id_prefix}:{sutta_ref}:{i}"))
        result.append(c)
    return result


# ---------------------------------------------------------------------------
# Embed + upsert helper
# ---------------------------------------------------------------------------

async def embed_and_upsert(client_q: QdrantClient, settings, chunks: list[dict]) -> int:
    total = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        embs  = await embed_texts([c["text"] for c in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(id=c.pop("_id"), vector=e, payload=c)
            for c, e in zip(batch, embs)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)
    return total


# ---------------------------------------------------------------------------
# Digha Nikaya (DN 1–34, predictable URLs)
# ---------------------------------------------------------------------------

async def ingest_dn(client_q: QdrantClient, settings) -> int:
    logger.info("=== Digha Nikaya (DN 1–34) ===")
    sem   = asyncio.Semaphore(8)
    total = 0

    async with httpx.AsyncClient() as http:
        for n in range(1, 35):
            url  = f"{SC_RAW}/dn/dn{n}_translation-en-sujato.json"
            data = await fetch_raw(http, sem, url)
            if not data:
                logger.warning("DN %d not found — skipping", n)
                continue

            sutta_ref = f"DN {n}"
            book      = f"Digha Nikaya – DN {n}"
            chunks    = parse_bilara(data, sutta_ref, book, "DN")

            upserted = await embed_and_upsert(client_q, settings, chunks)
            total   += upserted

            if n % 10 == 0:
                logger.info("DN: processed up to DN %d — %d chunks so far", n, total)

    logger.info("Digha Nikaya complete: %d chunks", total)
    return total


# ---------------------------------------------------------------------------
# Generic discovery-based ingestion (Snp, Thag, Thig)
# ---------------------------------------------------------------------------

async def ingest_kn_collection(
    client_q: QdrantClient,
    settings,
    gh_path: str,       # e.g. "kn/snp"
    book_name: str,     # e.g. "Sutta Nipata"
    id_prefix: str,     # e.g. "Snp"
) -> int:
    logger.info("=== %s (%s) ===", book_name, gh_path)
    api_sem = asyncio.Semaphore(3)
    raw_sem = asyncio.Semaphore(10)
    total   = 0

    async with httpx.AsyncClient() as http:
        top_entries = await github_list(http, api_sem, gh_path)
        await asyncio.sleep(1.5)

        file_urls: list[tuple[str, str]] = []

        for entry in top_entries:
            if entry.get("type") == "dir":
                # One level of subdirectory (e.g. Sutta Nipata's vagga1-5)
                subdir_entries = await github_list(http, api_sem, f"{gh_path}/{entry['name']}")
                await asyncio.sleep(1.0)
                for sub in subdir_entries:
                    fname = sub.get("name", "")
                    if not fname.endswith("_translation-en-sujato.json"):
                        continue
                    sutta_id_raw = fname.split("_translation")[0]
                    dl_url = sub.get("download_url", "")
                    if dl_url:
                        file_urls.append((sutta_id_raw, dl_url))
            else:
                fname = entry.get("name", "")
                if not fname.endswith("_translation-en-sujato.json"):
                    continue
                sutta_id_raw = fname.split("_translation")[0]
                dl_url       = entry.get("download_url", "")
                if dl_url:
                    file_urls.append((sutta_id_raw, dl_url))

        logger.info("%s: discovered %d translation files", book_name, len(file_urls))

        for file_idx, (sutta_id_raw, dl_url) in enumerate(file_urls):
            data = await fetch_raw(http, raw_sem, dl_url)
            if not data:
                continue

            # e.g. "snp4.1" → "Snp 4.1"
            prefix_lower = id_prefix.lower()
            if sutta_id_raw.startswith(prefix_lower):
                ref_suffix = sutta_id_raw[len(prefix_lower):]
            else:
                ref_suffix = sutta_id_raw
            sutta_ref = f"{id_prefix} {ref_suffix}"

            chunks = parse_bilara(data, sutta_ref, book_name, id_prefix)

            upserted = await embed_and_upsert(client_q, settings, chunks)
            total   += upserted

            if file_idx % 20 == 0:
                logger.info("%s: %d / %d files — %d chunks so far",
                            book_name, file_idx + 1, len(file_urls), total)

    logger.info("%s complete: %d chunks", book_name, total)
    return total


# ---------------------------------------------------------------------------
# Diamond Sutra (Project Gutenberg #64623)
# ---------------------------------------------------------------------------

DIAMOND_SUTRA_URL = "https://www.gutenberg.org/cache/epub/64623/pg64623.txt"
DIAMOND_TRANSLATION = "The Diamond Sutra (A.F. Price & Wong Mou-lam translation, Public Domain)"


def _extract_gutenberg_body(raw: str) -> str:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    start = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG", raw, re.IGNORECASE)
    end   = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG", raw, re.IGNORECASE)
    if start and end:
        return raw[start.end():end.start()]
    return raw


async def ingest_diamond_sutra(client_q: QdrantClient, settings) -> int:
    logger.info("=== Diamond Sutra (PG #64623) ===")
    skip_kws = {"gutenberg", "produced by", "www.gutenberg", "ebook", "transcriber"}

    async with httpx.AsyncClient(headers={"User-Agent": "CrossVerse-Ingestion/1.0"},
                                  follow_redirects=True, timeout=60) as http:
        for attempt in range(3):
            try:
                r = await http.get(DIAMOND_SUTRA_URL)
                if r.status_code == 200:
                    raw = r.text
                    break
            except Exception as e:
                logger.warning("Diamond Sutra attempt %d: %s", attempt + 1, e)
                await asyncio.sleep(2 ** attempt)
        else:
            logger.error("Could not fetch Diamond Sutra")
            return 0

    body  = _extract_gutenberg_body(raw)
    lines = body.splitlines()

    # Split into ~200-word chunks, respecting section breaks
    section_re = re.compile(r"^(CHAPTER|SECTION|PART)\s+[IVXLC\d]+", re.IGNORECASE)
    chunks: list[dict] = []
    buf_words: list[str] = []
    buf_parts: list[str] = []
    chunk_idx = 0

    def flush():
        nonlocal chunk_idx
        if buf_parts:
            text = re.sub(r"\s+", " ", " ".join(buf_parts)).strip()
            if len(text.split()) >= 8:
                chunks.append({
                    "religion":    RELIGION,
                    "text":        text,
                    "translation": DIAMOND_TRANSLATION,
                    "book":        "The Diamond Sutra",
                    "chapter":     None,
                    "verse":       chunk_idx + 1,
                    "reference":   f"Diamond Sutra {chunk_idx + 1}",
                    "source_url":  DIAMOND_SUTRA_URL,
                    "_id": str(uuid.uuid5(uuid.NAMESPACE_DNS,
                                          f"Buddhism:DiamondSutra:{chunk_idx}")),
                })
                chunk_idx += 1
            buf_words.clear()
            buf_parts.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(kw in stripped.lower() for kw in skip_kws):
            continue
        if section_re.match(stripped):
            flush()
            continue
        words = stripped.split()
        if len(buf_words) + len(words) > 200 and buf_words:
            flush()
        buf_words.extend(words)
        buf_parts.append(stripped)

    flush()
    logger.info("Diamond Sutra: %d chunks", len(chunks))

    total = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        embs  = await embed_texts([c["text"] for c in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(id=c.pop("_id"), vector=e, payload=c)
            for c, e in zip(batch, embs)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)

    logger.info("Diamond Sutra complete: %d chunks ingested", total)
    return total


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def ingest_buddhist_more():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    dn_total      = await ingest_dn(client_q, settings)
    snp_total     = await ingest_kn_collection(client_q, settings, "kn/snp",  "Sutta Nipata", "Snp")
    thag_total    = await ingest_kn_collection(client_q, settings, "kn/thag", "Theragatha",   "Thag")
    thig_total    = await ingest_kn_collection(client_q, settings, "kn/thig", "Therigatha",   "Thig")
    diamond_total = await ingest_diamond_sutra(client_q, settings)

    logger.info(
        "Buddhist More ingestion complete. DN=%d Snp=%d Thag=%d Thig=%d Diamond=%d  Total=%d",
        dn_total, snp_total, thag_total, thig_total, diamond_total,
        dn_total + snp_total + thag_total + thig_total + diamond_total,
    )


if __name__ == "__main__":
    asyncio.run(ingest_buddhist_more())
