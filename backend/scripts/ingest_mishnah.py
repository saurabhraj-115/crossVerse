"""
Ingest the complete Mishnah (63 tractates, ~4,200 mishnayot) via the Sefaria API.
Skips Pirkei Avot (ingested separately by ingest_pirkei_avot.py).
Translation: Sefaria / William Davidson Talmud Translation (CC BY-SA).
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

RELIGION    = "Judaism"
TRANSLATION = "Mishnah (Sefaria / William Davidson, CC BY-SA)"
BATCH_SIZE  = 20
CONCURRENCY = 6

# (sefaria_name, order, max_chapters)
# max_chapters is a ceiling — fetch halts automatically on 404/empty.
# Pirkei Avot (Nezikin order) is excluded — ingested separately.
TRACTATES = [
    # Zeraim
    ("Mishnah Berakhot",      "Zeraim",   9),
    ("Mishnah Peah",          "Zeraim",   8),
    ("Mishnah Demai",         "Zeraim",   7),
    ("Mishnah Kilayim",       "Zeraim",   9),
    ("Mishnah Sheviit",       "Zeraim",  10),
    ("Mishnah Terumot",       "Zeraim",  11),
    ("Mishnah Maasrot",       "Zeraim",   5),
    ("Mishnah Maaser Sheni",  "Zeraim",   5),
    ("Mishnah Challah",       "Zeraim",   4),
    ("Mishnah Orlah",         "Zeraim",   3),
    ("Mishnah Bikkurim",      "Zeraim",   3),
    # Moed
    ("Mishnah Shabbat",       "Moed",    24),
    ("Mishnah Eruvin",        "Moed",    10),
    ("Mishnah Pesachim",      "Moed",    10),
    ("Mishnah Shekalim",      "Moed",    8),
    ("Mishnah Yoma",          "Moed",    8),
    ("Mishnah Sukkah",        "Moed",    5),
    ("Mishnah Beitzah",       "Moed",    5),
    ("Mishnah Rosh Hashanah", "Moed",    4),
    ("Mishnah Taanit",        "Moed",    4),
    ("Mishnah Megillah",      "Moed",    4),
    ("Mishnah Moed Katan",    "Moed",    3),
    ("Mishnah Chagigah",      "Moed",    3),
    # Nashim
    ("Mishnah Yevamot",       "Nashim", 16),
    ("Mishnah Ketubot",       "Nashim", 13),
    ("Mishnah Nedarim",       "Nashim", 11),
    ("Mishnah Nazir",         "Nashim",  9),
    ("Mishnah Sotah",         "Nashim",  9),
    ("Mishnah Gittin",        "Nashim",  9),
    ("Mishnah Kiddushin",     "Nashim",  4),
    # Nezikin (Avot excluded)
    ("Mishnah Bava Kamma",    "Nezikin", 10),
    ("Mishnah Bava Metzia",   "Nezikin", 10),
    ("Mishnah Bava Batra",    "Nezikin", 10),
    ("Mishnah Sanhedrin",     "Nezikin", 11),
    ("Mishnah Makkot",        "Nezikin",  3),
    ("Mishnah Shevuot",       "Nezikin",  8),
    ("Mishnah Eduyot",        "Nezikin",  8),
    ("Mishnah Avodah Zarah",  "Nezikin",  5),
    ("Mishnah Horayot",       "Nezikin",  3),
    # Kodashim
    ("Mishnah Zevachim",      "Kodashim", 14),
    ("Mishnah Menachot",      "Kodashim", 13),
    ("Mishnah Chullin",       "Kodashim", 12),
    ("Mishnah Bekhorot",      "Kodashim",  9),
    ("Mishnah Arachin",       "Kodashim",  9),
    ("Mishnah Temurah",       "Kodashim",  7),
    ("Mishnah Keritot",       "Kodashim",  6),
    ("Mishnah Meilah",        "Kodashim",  6),
    ("Mishnah Tamid",         "Kodashim",  7),
    ("Mishnah Middot",        "Kodashim",  5),
    ("Mishnah Kinnim",        "Kodashim",  3),
    # Taharot
    ("Mishnah Keilim",        "Taharot", 30),
    ("Mishnah Oholot",        "Taharot", 18),
    ("Mishnah Negaim",        "Taharot", 14),
    ("Mishnah Parah",         "Taharot", 12),
    ("Mishnah Taharot",       "Taharot", 10),
    ("Mishnah Mikvaot",       "Taharot", 10),
    ("Mishnah Niddah",        "Taharot", 10),
    ("Mishnah Makhshirin",    "Taharot",  6),
    ("Mishnah Zavim",         "Taharot",  5),
    ("Mishnah Tevul Yom",     "Taharot",  4),
    ("Mishnah Yadayim",       "Taharot",  4),
    ("Mishnah Uktzin",        "Taharot",  3),
]


def stable_id(tractate: str, chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Judaism:Mishnah:{tractate}:{chapter}:{verse}"))


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


async def fetch_chapter(
    client: httpx.AsyncClient, sem: asyncio.Semaphore,
    tractate: str, order: str, chapter: int
) -> list[dict]:
    encoded = tractate.replace(" ", "%20")
    url     = f"https://www.sefaria.org/api/texts/{encoded}.{chapter}?lang=en&context=0&pad=0"
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    raw  = data.get("text", [])
                    if not raw:
                        return []
                    verses = []
                    for i, vt in enumerate(raw, start=1):
                        if isinstance(vt, list):
                            vt = " ".join(vt)
                        text = strip_html(str(vt)).strip()
                        if not text:
                            continue
                        # Short name for display (strip "Mishnah " prefix)
                        short = tractate.replace("Mishnah ", "")
                        verses.append({
                            "religion":    RELIGION,
                            "text":        text,
                            "translation": TRANSLATION,
                            "book":        f"Mishnah – {order} – {short}",
                            "chapter":     chapter,
                            "verse":       i,
                            "reference":   f"{short} {chapter}:{i}",
                            "source_url":  f"https://www.sefaria.org/{encoded}.{chapter}.{i}",
                        })
                    return verses
                if r.status_code == 404:
                    return []
            except Exception as e:
                if attempt == 2:
                    logger.warning("Failed %s ch.%d — %s", tractate, chapter, e)
                await asyncio.sleep(1)
    return []


async def ingest_tractate(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    tractate: str,
    order: str,
    max_chapters: int,
) -> list[dict]:
    all_verses: list[dict] = []
    for ch in range(1, max_chapters + 1):
        verses = await fetch_chapter(client, sem, tractate, order, ch)
        if not verses and ch > 1:
            break   # chapter not found — tractate finished
        all_verses.extend(verses)
    return all_verses


async def ingest_mishnah():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem      = asyncio.Semaphore(CONCURRENCY)
    grand_total = 0

    async with httpx.AsyncClient() as http:
        for tractate, order, max_ch in TRACTATES:
            logger.info("Ingesting %s (%s)…", tractate, order)
            all_verses = await ingest_tractate(http, sem, tractate, order, max_ch)

            if not all_verses:
                logger.warning("  No verses fetched for %s", tractate)
                continue

            total = 0
            for i in range(0, len(all_verses), BATCH_SIZE):
                batch      = all_verses[i : i + BATCH_SIZE]
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

            grand_total += total
            logger.info("  %s: %d mishnayot ingested", tractate, total)

    logger.info("Mishnah ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_mishnah())
