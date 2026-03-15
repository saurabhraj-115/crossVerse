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
from scripts.ingest_gita import ingest_gita
from scripts.ingest_dhammapada import ingest_dhammapada
from scripts.ingest_guru_granth import ingest_guru_granth
from scripts.ingest_torah import ingest_torah

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

INGESTION_STEPS = [
    ("Bhagavad Gita (Hinduism)", ingest_gita),
    ("Dhammapada (Buddhism)", ingest_dhammapada),
    ("Guru Granth Sahib (Sikhism)", ingest_guru_granth),
    ("Quran (Islam)", ingest_quran),
    ("Bible KJV (Christianity)", ingest_bible),
    ("Torah/Tanakh (Judaism)", ingest_torah),
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
