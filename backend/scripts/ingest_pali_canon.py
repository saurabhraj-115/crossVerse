"""
Ingest the Pali Canon (Majjhima, Samyutta, Anguttara Nikaya) from SuttaCentral sc-data.
Translation: Bhikkhu Sujato (CC0 public domain).

  - Majjhima Nikaya  (MN 1–152)  ~10,000 chunks
  - Samyutta Nikaya  (SN 1–56)   ~18,000 chunks
  - Anguttara Nikaya (AN 1–11)   ~18,000 chunks

File discovery for SN and AN uses the GitHub Contents API (60 req/hour unauthenticated).
Set GITHUB_TOKEN env var for higher limits (5,000 req/hour).
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
MAX_WORDS   = 200   # target words per chunk

SC_RAW = "https://raw.githubusercontent.com/suttacentral/sc-data/main/sc_bilara_data/translation/en/sujato/sutta"
GH_API = "https://api.github.com/repos/suttacentral/sc-data/contents/sc_bilara_data/translation/en/sujato/sutta"

MN_VAGGAS = {
    1:   "Mulapariyaya Vagga",   11:  "Minor Yoke Vagga",     21: "Householders Vagga",
    31:  "Lesser Lion's Roar Vagga", 41: "Brahmins Vagga",    51: "Lay Followers Vagga",
    61:  "Non-returners Vagga",  71:  "Travel Vagga",         81: "Bhikkhus Vagga",
    91:  "Kings Vagga",         101:  "Devadaha Vagga",       111: "Six Sets of Six Vagga",
    121: "Division of Emptiness",131: "Exposition Vagga",     141: "Truths Vagga",
    151: "Final Vagga",
}
_mn_vagga_starts = sorted(MN_VAGGAS.keys(), reverse=True)


def mn_vagga(n: int) -> str:
    for start in _mn_vagga_starts:
        if n >= start:
            return MN_VAGGAS[start]
    return "Majjhima Nikaya"


# ---------------------------------------------------------------------------
# GitHub helpers
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
# Bilara JSON → chunks
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
    # Collect valid segments in order
    segments: list[tuple[str, str]] = []
    for k, v in data.items():
        v = (v or "").strip()
        if not v:
            continue
        # Key pattern: id:section.segment  e.g. mn1:2.3  or sn1.1:4.1
        m = re.match(r"[^:]+:(\d+)\.", k)
        if m and m.group(1) == "0":
            continue   # title/header segment
        if not m:
            continue
        segments.append((k, v))

    if not segments:
        return []

    # Sort by key (lexicographic works for well-formed keys)
    segments.sort(key=lambda x: x[0])

    sutta_title = _sutta_title(data)
    display_book = f"{book_name} – {sutta_title}" if sutta_title else book_name

    chunks: list[dict] = []
    buf_words: list[str] = []
    buf_parts: list[str] = []
    chunk_idx = 0

    def flush():
        nonlocal chunk_idx
        if buf_parts:
            text = " ".join(buf_parts)
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

    # Assign stable IDs
    result = []
    for i, c in enumerate(chunks):
        c["_id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Buddhism:{id_prefix}:{sutta_ref}:{i}"))
        result.append(c)
    return result


# ---------------------------------------------------------------------------
# Majjhima Nikaya (MN 1–152, predictable URLs)
# ---------------------------------------------------------------------------

async def ingest_mn(client_q: QdrantClient, settings) -> int:
    logger.info("=== Majjhima Nikaya (MN 1–152) ===")
    sem = asyncio.Semaphore(8)
    total_chunks = 0

    async with httpx.AsyncClient() as http:
        for n in range(1, 153):
            url  = f"{SC_RAW}/mn/mn{n}_translation-en-sujato.json"
            data = await fetch_raw(http, sem, url)
            if not data:
                logger.warning("MN %d not found — skipping", n)
                continue

            vagga    = mn_vagga(n)
            book     = f"Majjhima Nikaya – {vagga}"
            sutta_ref = f"MN {n}"
            chunks   = parse_bilara(data, sutta_ref, book, "MN")

            # embed + upsert
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i : i + BATCH_SIZE]
                embs  = await embed_texts([c["text"] for c in batch], batch_size=BATCH_SIZE)
                points = [
                    PointStruct(id=c.pop("_id"), vector=e, payload=c)
                    for c, e in zip(batch, embs)
                ]
                client_q.upsert(collection_name=settings.qdrant_collection, points=points)
                total_chunks += len(points)

            if n % 20 == 0:
                logger.info("MN: processed up to MN %d — %d chunks so far", n, total_chunks)

    logger.info("Majjhima Nikaya complete: %d chunks", total_chunks)
    return total_chunks


# ---------------------------------------------------------------------------
# Generic Nikaya via GitHub discovery (SN, AN)
# ---------------------------------------------------------------------------

async def discover_and_ingest_nikaya(
    client_q: QdrantClient,
    settings,
    nikaya_short: str,    # "sn" | "an"
    nikaya_name: str,     # "Samyutta Nikaya" | "Anguttara Nikaya"
    ref_prefix: str,      # "SN" | "AN"
    num_subgroups: int,   # 56 for SN, 11 for AN
) -> int:
    logger.info("=== %s ===", nikaya_name)
    api_sem = asyncio.Semaphore(3)   # conservative for GitHub API
    raw_sem = asyncio.Semaphore(10)  # raw.githubusercontent has no rate limit
    total_chunks = 0

    async with httpx.AsyncClient() as http:
        # Step 1: discover all translation files
        all_file_urls: list[tuple[str, str]] = []   # (sutta_id, download_url)

        for sg in range(1, num_subgroups + 1):
            subgroup = f"{nikaya_short}{sg}"
            entries  = await github_list(http, api_sem, f"{nikaya_short}/{subgroup}")
            await asyncio.sleep(1.5)  # be polite to GitHub API

            for entry in entries:
                fname = entry.get("name", "")
                if not fname.endswith("_translation-en-sujato.json"):
                    continue
                # Extract sutta ID from filename: e.g. "sn1.1-10_translation..."  → "sn1.1"
                sutta_id_raw = fname.split("_translation")[0]
                download_url = entry.get("download_url", "")
                if download_url:
                    all_file_urls.append((sutta_id_raw, download_url))

        logger.info("%s: discovered %d translation files", nikaya_name, len(all_file_urls))

        # Step 2: fetch + parse + embed each file
        for file_idx, (sutta_id_raw, dl_url) in enumerate(all_file_urls):
            data = await fetch_raw(http, raw_sem, dl_url)
            if not data:
                continue

            # Build a human-readable reference from the sutta_id_raw
            # e.g. "sn1.1-10" → "SN 1.1-10"
            ref_display = f"{ref_prefix} {sutta_id_raw[len(nikaya_short):]}"
            book = f"{nikaya_name}"
            chunks = parse_bilara(data, ref_display, book, f"{ref_prefix}:{sutta_id_raw}")

            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i : i + BATCH_SIZE]
                embs  = await embed_texts([c["text"] for c in batch], batch_size=BATCH_SIZE)
                points = [
                    PointStruct(id=c.pop("_id"), vector=e, payload=c)
                    for c, e in zip(batch, embs)
                ]
                client_q.upsert(collection_name=settings.qdrant_collection, points=points)
                total_chunks += len(points)

            if file_idx % 50 == 0:
                logger.info("%s: %d / %d files — %d chunks so far",
                            nikaya_name, file_idx + 1, len(all_file_urls), total_chunks)

    logger.info("%s complete: %d chunks", nikaya_name, total_chunks)
    return total_chunks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def ingest_pali_canon():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    mn_total = await ingest_mn(client_q, settings)
    sn_total = await discover_and_ingest_nikaya(
        client_q, settings, "sn", "Samyutta Nikaya", "SN", 56
    )
    an_total = await discover_and_ingest_nikaya(
        client_q, settings, "an", "Anguttara Nikaya", "AN", 11
    )

    logger.info("Pali Canon ingestion complete. MN=%d SN=%d AN=%d  Total=%d",
                mn_total, sn_total, an_total, mn_total + sn_total + an_total)


if __name__ == "__main__":
    asyncio.run(ingest_pali_canon())
