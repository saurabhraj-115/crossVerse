"""
Ingest the complete Dhammapada (all 423 verses) from SuttaCentral sc-data GitHub.
Uses Bhikkhu Sujato's English translation (CC0 public domain).
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

RELIGION    = "Buddhism"
TRANSLATION = "Dhammapada (Bhikkhu Sujato, CC0)"
BATCH_SIZE  = 20

BASE_RAW = (
    "https://raw.githubusercontent.com/suttacentral/sc-data/master/"
    "sc_bilara_data/translation/en/sujato/sutta/kn/dhp/{filename}"
)

# All 26 files in the repo (covers dhp1–dhp423)
FILES = [
    "dhp1-20_translation-en-sujato.json",
    "dhp21-32_translation-en-sujato.json",
    "dhp33-43_translation-en-sujato.json",
    "dhp44-59_translation-en-sujato.json",
    "dhp60-75_translation-en-sujato.json",
    "dhp76-89_translation-en-sujato.json",
    "dhp90-99_translation-en-sujato.json",
    "dhp100-115_translation-en-sujato.json",
    "dhp116-128_translation-en-sujato.json",
    "dhp129-145_translation-en-sujato.json",
    "dhp146-156_translation-en-sujato.json",
    "dhp157-166_translation-en-sujato.json",
    "dhp167-178_translation-en-sujato.json",
    "dhp179-196_translation-en-sujato.json",
    "dhp197-208_translation-en-sujato.json",
    "dhp209-220_translation-en-sujato.json",
    "dhp221-234_translation-en-sujato.json",
    "dhp235-255_translation-en-sujato.json",
    "dhp256-272_translation-en-sujato.json",
    "dhp273-289_translation-en-sujato.json",
    "dhp290-305_translation-en-sujato.json",
    "dhp306-319_translation-en-sujato.json",
    "dhp320-333_translation-en-sujato.json",
    "dhp334-359_translation-en-sujato.json",
    "dhp360-382_translation-en-sujato.json",
    "dhp383-423_translation-en-sujato.json",
]

# Vagga (chapter) names mapped by verse range start
VAGGA_MAP = {
    1: "Yamakavagga (Pairs)",
    21: "Appamadavagga (Diligence)",
    33: "Cittavagga (The Mind)",
    44: "Pupphavagga (Flowers)",
    60: "Balavagga (The Fool)",
    76: "Panditavagga (The Astute)",
    90: "Arahantavagga (The Perfected Ones)",
    100: "Sahassavagga (Thousands)",
    116: "Papavagga (Evil)",
    129: "Dandavagga (The Rod)",
    146: "Jaravagga (Old Age)",
    157: "Attavagga (The Self)",
    167: "Lokavagga (The World)",
    179: "Buddhavagga (The Awakened One)",
    197: "Sukhavagga (Happiness)",
    209: "Piyavagga (The Dear)",
    221: "Kodhavagga (Anger)",
    235: "Malavagga (Corruption)",
    256: "Dhammattavagga (The Just)",
    273: "Maggavagga (The Path)",
    290: "Pakinnakavagga (Miscellaneous)",
    306: "Nirayavagga (Hell)",
    320: "Nagavagga (The Elephant)",
    334: "Tanhavagga (Craving)",
    360: "Bhikkhuvagga (The Monk)",
    383: "Brahmanavagga (The Brahmin)",
}

_vagga_starts = sorted(VAGGA_MAP.keys(), reverse=True)


def verse_vagga(verse_num: int) -> str:
    for start in _vagga_starts:
        if verse_num >= start:
            return VAGGA_MAP[start]
    return "Dhammapada"


def stable_id(verse_num: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Buddhism:Dhammapada:{verse_num}"))


async def fetch_file(client: httpx.AsyncClient, sem: asyncio.Semaphore,
                     filename: str) -> dict[int, list[str]]:
    """Returns {verse_num: [line1, line2, ...]} for the file."""
    url = BASE_RAW.format(filename=filename)
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    verses: dict[int, list[str]] = {}
                    for key, text in data.items():
                        # key format: "dhp{verse}:{line}" or "dhp{verse}:{line}.{sub}"
                        # Skip header/metadata lines (line == 0 or has sub-parts like 0.1)
                        m = re.match(r"dhp(\d+):(\d+(?:\.\d+)?)$", key)
                        if not m:
                            continue
                        verse_num = int(m.group(1))
                        line_id = m.group(2)
                        # Skip header lines (line 0.x)
                        if line_id.startswith("0"):
                            continue
                        text = text.strip().rstrip()
                        if text:
                            verses.setdefault(verse_num, []).append(text)
                    return verses
                elif r.status_code == 404:
                    logger.warning("File not found: %s", filename)
                    return {}
            except Exception as e:
                if attempt == 2:
                    logger.warning("Failed %s — %s", filename, e)
                await asyncio.sleep(1)
    return {}


async def ingest_dhammapada_full():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem = asyncio.Semaphore(10)

    logger.info("Fetching all Dhammapada files from SuttaCentral sc-data …")
    async with httpx.AsyncClient() as http:
        tasks = [fetch_file(http, sem, f) for f in FILES]
        results = await asyncio.gather(*tasks)

    # Merge all verse dicts
    all_verse_lines: dict[int, list[str]] = {}
    for vd in results:
        for vnum, lines in vd.items():
            all_verse_lines.setdefault(vnum, []).extend(lines)

    # Build flat verse list, joining lines into a single text per verse
    verses = []
    for vnum in sorted(all_verse_lines.keys()):
        lines = all_verse_lines[vnum]
        text = " ".join(lines).strip()
        if not text:
            continue
        vagga = verse_vagga(vnum)
        verses.append({
            "religion":    RELIGION,
            "text":        text,
            "translation": TRANSLATION,
            "book":        f"Dhammapada – {vagga}",
            "chapter":     None,
            "verse":       vnum,
            "reference":   f"Dhp {vnum}",
            "source_url":  BASE_RAW.format(filename="dhp1-20_translation-en-sujato.json"),
        })

    logger.info("Parsed %d Dhammapada verses", len(verses))

    total = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch = verses[i: i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(
                id=stable_id(v["verse"]),
                vector=emb,
                payload=v,
            )
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)
        logger.info("Upserted %d / %d", total, len(verses))

    logger.info("Dhammapada (full) ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_dhammapada_full())
