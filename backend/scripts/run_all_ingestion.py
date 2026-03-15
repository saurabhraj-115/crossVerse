"""
Run all ingestion scripts sequentially.

Usage:
    cd backend
    python -m scripts.run_all_ingestion
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ingest_bible import ingest_bible
from scripts.ingest_quran import ingest_quran
from scripts.ingest_gita_full import ingest_gita_full
from scripts.ingest_dhammapada_full import ingest_dhammapada_full
from scripts.ingest_yoga_sutras_full import ingest_yoga_sutras_full
from scripts.ingest_guru_granth_full import ingest_guru_granth_full
from scripts.ingest_tanakh_full import ingest_tanakh_full
from scripts.ingest_hadith_full import ingest_hadith_full
from scripts.ingest_upanishads_full import ingest_upanishads_full

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

INGESTION_STEPS = [
    # Hinduism
    ("Bhagavad Gita – full 700 verses", ingest_gita_full),
    ("Yoga Sutras – full 196 sutras", ingest_yoga_sutras_full),
    ("Upanishads – 12 principal", ingest_upanishads_full),
    # Buddhism
    ("Dhammapada – full 423 verses", ingest_dhammapada_full),
    # Sikhism
    ("Guru Granth Sahib – full 1430 angs", ingest_guru_granth_full),
    # Islam
    ("Quran – complete", ingest_quran),
    ("Hadith – Sahih Bukhari", ingest_hadith_full),
    # Christianity
    ("Bible KJV – complete", ingest_bible),
    # Judaism
    ("Tanakh – full 39 books", ingest_tanakh_full),
]


async def run_all():
    logger.info("=" * 60)
    logger.info("CrossVerse Full Ingestion Pipeline")
    logger.info("=" * 60)

    for name, fn in INGESTION_STEPS:
        logger.info("\n--- Starting: %s ---", name)
        try:
            await fn()
            logger.info("--- Completed: %s ---\n", name)
        except Exception as exc:
            logger.error("--- FAILED: %s | Error: %s ---\n", name, exc)
            # Continue with next scripture even if one fails
            continue

    logger.info("=" * 60)
    logger.info("All ingestion complete.")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all())
