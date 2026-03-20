"""
Delete low-quality scripture points from Qdrant:
  - Any point where text has fewer than 8 words
  - Zoroastrianism points with footnote patterns (roman numerals, page refs)
  - Taoism points that are clearly over-parsed (single sentence fragments)
"""

from __future__ import annotations

import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import PointIdsList

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Zoroastrianism footnote pattern: starts with roman numerals or page refs like "iv:12" or "p. 34"
_ZOROASTRIAN_FOOTNOTE_RE = re.compile(
    r"^[ivxlcmIVXLCM]+[\.:]\d+|^p\.\s*\d+|^\d+\s*\."
)


def is_low_quality(payload: dict) -> bool:
    """Return True if the point should be deleted."""
    text = (payload.get("text") or "").strip()

    # Universal: fewer than 8 words
    if len(text.split()) < 8:
        return True

    religion = (payload.get("religion") or "").strip()

    # Zoroastrianism-specific: footnote patterns
    if religion == "Zoroastrianism":
        if _ZOROASTRIAN_FOOTNOTE_RE.match(text):
            return True

    # Taoism-specific: very short fragments (already caught by word count, but
    # also catch single-sentence chunks under 15 words that look like headings)
    if religion == "Taoism":
        words = text.split()
        if len(words) < 15 and text.endswith(":"):
            return True

    return False


def clean_quality():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    collection_name = settings.qdrant_collection
    logger.info("Scanning collection '%s' for low-quality points…", collection_name)

    ids_to_delete: list[str | int] = []
    deleted_per_religion: dict[str, int] = defaultdict(int)

    offset = None
    scanned = 0
    SCROLL_LIMIT = 100

    while True:
        results, next_offset = client_q.scroll(
            collection_name=collection_name,
            offset=offset,
            limit=SCROLL_LIMIT,
            with_payload=True,
            with_vectors=False,
        )

        for point in results:
            scanned += 1
            payload = point.payload or {}
            if is_low_quality(payload):
                ids_to_delete.append(point.id)
                religion = (payload.get("religion") or "unknown").strip()
                deleted_per_religion[religion] += 1

        if scanned % 10000 == 0:
            logger.info("  Scanned %d points, found %d to delete so far…",
                        scanned, len(ids_to_delete))

        if next_offset is None:
            break
        offset = next_offset

    logger.info("Scan complete. Scanned %d points total, %d marked for deletion.",
                scanned, len(ids_to_delete))

    if not ids_to_delete:
        logger.info("Nothing to delete.")
        return

    # Delete in batches of 500
    BATCH = 500
    total_deleted = 0
    for i in range(0, len(ids_to_delete), BATCH):
        batch = ids_to_delete[i : i + BATCH]
        client_q.delete(
            collection_name=collection_name,
            points_selector=PointIdsList(points=batch),
        )
        total_deleted += len(batch)
        logger.info("  Deleted %d / %d points…", total_deleted, len(ids_to_delete))

    logger.info("Deletion complete. Total deleted: %d", total_deleted)
    logger.info("Breakdown by religion:")
    for religion, count in sorted(deleted_per_religion.items()):
        logger.info("  %-25s %d", religion, count)


if __name__ == "__main__":
    clean_quality()
