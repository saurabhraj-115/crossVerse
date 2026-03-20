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
from scripts.ingest_upanishads_more import ingest_upanishads_more
from scripts.ingest_bhagavatam import ingest_bhagavatam
from scripts.ingest_ramayana import ingest_ramayana
from scripts.ingest_mahabharata import ingest_mahabharata
from scripts.ingest_manusmriti import ingest_manusmriti
from scripts.ingest_vedas import ingest_vedas
from scripts.ingest_pali_canon import ingest_pali_canon
from scripts.ingest_hadith_extra import ingest_hadith_extra
from scripts.ingest_pirkei_avot import ingest_pirkei_avot
from scripts.ingest_mishnah import ingest_mishnah
from scripts.ingest_confucianism import ingest_confucianism
from scripts.ingest_taoism import ingest_taoism
from scripts.ingest_jainism import ingest_jainism
from scripts.ingest_zoroastrianism import ingest_zoroastrianism
from scripts.ingest_hadith_more import ingest_hadith_more
from scripts.ingest_talmud import ingest_talmud
from scripts.ingest_buddhist_more import ingest_buddhist_more
from scripts.ingest_apocrypha import ingest_apocrypha
from scripts.ingest_church_fathers import ingest_church_fathers
from scripts.ingest_bahai import ingest_bahai
from scripts.ingest_shinto import ingest_shinto

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

INGESTION_STEPS = [
    # Hinduism
    ("Bhagavad Gita – full 700 verses", ingest_gita_full),
    ("Yoga Sutras – full 196 sutras", ingest_yoga_sutras_full),
    ("Upanishads – Isa/Katha/Kena (Paramananda)", ingest_upanishads_full),
    ("Upanishads – 9 more (Chandogya, Aitareya, Kaushitaki, Mundaka, Taittiriya, Brihadaranyaka, Svetasvatara, Maitrayani, Prashna)", ingest_upanishads_more),
    ("Bhagavata Purana – 12 Cantos", ingest_bhagavatam),
    ("Ramayana – Griffith translation", ingest_ramayana),
    ("Mahabharata – Ganguli translation (18 Parvas)", ingest_mahabharata),
    ("Manusmriti – Bühler translation (12 chapters)", ingest_manusmriti),
    ("The Four Vedas – Griffith translations", ingest_vedas),
    # Buddhism
    ("Dhammapada – full 423 verses", ingest_dhammapada_full),
    ("Pali Canon – Majjhima, Samyutta & Anguttara Nikaya (SuttaCentral)", ingest_pali_canon),
    # Sikhism
    ("Guru Granth Sahib – full 1430 angs", ingest_guru_granth_full),
    # Islam
    ("Quran – complete", ingest_quran),
    ("Hadith – Sahih Bukhari", ingest_hadith_full),
    ("Hadith – Sahih Muslim, Nawawi 40, Abu Dawud", ingest_hadith_extra),
    # Christianity
    ("Bible KJV – complete", ingest_bible),
    # Judaism
    ("Tanakh – full 39 books", ingest_tanakh_full),
    ("Pirkei Avot – 6 chapters (Sefaria)", ingest_pirkei_avot),
    ("Mishnah – 62 tractates / 6 orders (Sefaria)", ingest_mishnah),
    # Confucianism
    ("Analects of Confucius + Great Learning (James Legge)", ingest_confucianism),
    # Taoism
    ("Tao Te Ching (James Legge)", ingest_taoism),
    # Jainism
    ("Uttaradhyayana + Sutrakritanga (Hermann Jacobi)", ingest_jainism),
    # Zoroastrianism
    ("Vendidad + Zend-Avesta (Darmesteter)", ingest_zoroastrianism),
    # Islam — additional Hadith
    ("Hadith – Tirmidhi, Ibn Majah, Riyad as-Salihin", ingest_hadith_more),
    # Judaism — Talmud
    ("Babylonian Talmud – key tractates (Sefaria)", ingest_talmud),
    # Buddhism — additional Nikayas
    ("Buddhist texts – DN, Sutta Nipata, Theragatha, Therigatha", ingest_buddhist_more),
    # Christianity — Apocrypha + Church Fathers
    ("Christian Apocrypha (KJV Apocrypha, Gutenberg)", ingest_apocrypha),
    ("Early Church Fathers – Clement, Ignatius, Justin Martyr", ingest_church_fathers),
    # Bahá'í
    ("Bahá'í – Hidden Words, Seven Valleys, Gleanings", ingest_bahai),
    # Shinto
    ("Shinto – Kojiki + Nihongi (Chamberlain/Aston)", ingest_shinto),
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
