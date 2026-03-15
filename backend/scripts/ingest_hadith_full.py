"""
Ingest Sahih Bukhari (7,563 hadiths) from the fawazahmed0/hadith-api GitHub CDN.
Free, no API key, single JSON download.
Generates deterministic IDs so re-running is safe (upsert = no duplicates).
"""

from __future__ import annotations

import asyncio
import logging
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

RELIGION    = "Islam"
TRANSLATION = "Sahih Bukhari (Siddiqui, Public Domain)"
BATCH_SIZE  = 20

# fawazahmed0/hadith-api: single JSON with all hadiths
BUKHARI_URL = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/eng-bukhari.json"
MUSLIM_URL  = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/eng-muslim.json"

# Book names for Bukhari (volume-based)
BUKHARI_BOOKS = {
    1: "Revelation", 2: "Belief", 3: "Knowledge", 4: "Ablutions",
    5: "Bathing", 6: "Menstrual Periods", 7: "Rubbing Hands & Feet with Dust",
    8: "Prayer", 9: "Prayer Hall", 10: "Times of Prayer", 11: "Call to Prayer",
    12: "Characteristics of Prayer", 13: "Friday Prayer", 14: "Fear Prayer",
    15: "Festivals", 16: "Witr Prayer", 17: "Invoking Allah for Rain",
    18: "Eclipses", 19: "Prostration During Quran Recitation",
    20: "Shortening Prayers", 21: "Night Prayer", 22: "Actions While Praying",
    23: "Funerals", 24: "Obligatory Charity Tax", 25: "Pilgrimage",
    26: "Minor Pilgrimage", 27: "Pilgrimage – Penalty of Hunting",
    28: "Virtues of Madinah", 29: "Fasting", 30: "Tarawih Prayer",
    31: "Night of Power", 32: "Retiring to Mosque", 33: "Sales and Trade",
    34: "Sales in which a Price is paid", 35: "Representation",
    36: "Agriculture", 37: "Water", 38: "Loans", 39: "Lost Property",
    40: "Oppressions", 41: "Partnership", 42: "Mortgaging",
    43: "Freeing Slaves", 44: "Gifts", 45: "Witnesses", 46: "Peacemaking",
    47: "Conditions", 48: "Wills and Testaments", 49: "Fighting for Allah",
    50: "One-fifth of Booty", 51: "Beginning of Creation",
    52: "Prophets", 53: "Virtues and Merits of the Prophet",
    54: "Companions of the Prophet", 55: "Merits of Al-Ansar",
    56: "Military Expeditions", 57: "Quran", 58: "Wedlock and Marriage",
    59: "Divorce", 60: "Supporting the Family", 61: "Food & Meals",
    62: "Sacrifice on Occasion of Birth", 63: "Hunting and Slaughtering",
    64: "Al-Adha Festival Sacrifice", 65: "Drinks", 66: "Patients",
    67: "Medicine", 68: "Dress", 69: "Good Manners and Form",
    70: "Asking Permission", 71: "Invocations", 72: "Softening the Heart",
    73: "Divine Will", 74: "Oaths and Vows", 75: "Expiation for Unfulfilled Oaths",
    76: "Inheritance Laws", 77: "Limits and Punishments",
    78: "Blood Money", 79: "Apostates", 80: "Saying Something under Compulsion",
    81: "Tricks", 82: "Dreams", 83: "Afflictions and the End of the World",
    84: "Judgments", 85: "Wishes", 86: "Truthfulness",
    87: "Holding Steadfast", 88: "Oneness of Allah",
}


def stable_id(collection: str, hadith_num: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Islam:Hadith:{collection}:{hadith_num}"))


async def download_json(client: httpx.AsyncClient, url: str) -> dict | None:
    logger.info("Downloading %s …", url)
    for attempt in range(3):
        try:
            r = await client.get(url, timeout=120)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.warning("Attempt %d failed: %s", attempt + 1, e)
            await asyncio.sleep(3)
    return None


def parse_hadiths(data: dict, collection_name: str, book_map: dict) -> list[dict]:
    hadiths_raw = data.get("hadiths", [])
    verses = []
    for h in hadiths_raw:
        text = (h.get("text") or "").strip()
        if not text or len(text) < 20:
            continue
        num = h.get("hadithnumber") or h.get("arabicnumber") or 0
        book_num = h.get("book") or 0
        book_name = book_map.get(book_num, f"Book {book_num}")
        verses.append({
            "religion":    RELIGION,
            "text":        text,
            "translation": f"{collection_name} (Siddiqui, Public Domain)",
            "book":        f"{collection_name} – {book_name}",
            "chapter":     book_num,
            "verse":       num,
            "reference":   f"{collection_name} {num}",
            "source_url":  BUKHARI_URL,
        })
    return verses


async def ingest_hadith_full():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    async with httpx.AsyncClient() as http:
        data = await download_json(http, BUKHARI_URL)

    if not data:
        logger.error("Failed to download Bukhari JSON — aborting.")
        return

    verses = parse_hadiths(data, "Sahih Bukhari", BUKHARI_BOOKS)
    logger.info("Parsed %d Bukhari hadiths", len(verses))

    total = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch = verses[i: i + BATCH_SIZE]
        embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
        points = [
            PointStruct(
                id=stable_id("Bukhari", v["verse"]),
                vector=emb,
                payload=v,
            )
            for v, emb in zip(batch, embeddings)
        ]
        client_q.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)
        if total % 500 == 0 or total == len(verses):
            logger.info("Upserted %d / %d", total, len(verses))

    logger.info("Hadith (Sahih Bukhari) ingestion complete. Total: %d", total)


if __name__ == "__main__":
    asyncio.run(ingest_hadith_full())
