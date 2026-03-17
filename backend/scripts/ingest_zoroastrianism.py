"""
Ingest Zoroastrian scriptures from Sacred Texts Archive (Public Domain translations):
  - Gathas of Zarathustra / Yasna (L.H. Mills, SBE Vol 31) — 17 hymns, ~238 stanzas
  - Vendidad / Videvdat (James Darmesteter, SBE Vol 4) — 22 fargards (chapters)

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

RELIGION   = "Zoroastrianism"
BATCH_SIZE = 20

TEXTS = [
    {
        "name":        "Gathas of Zarathustra",
        "id_prefix":   "Gathas",
        "translation": "Gathas (L.H. Mills, Sacred Books of the East Vol. 31, Public Domain)",
        "pages": [
            # Yasna 28–34 (Ahunavaiti Gatha)
            ("https://www.sacred-texts.com/zor/sbe31/sbe3104.htm", "Gathas – Yasna 28–34 (Ahunavaiti Gatha)", 28),
            # Yasna 43–46 (Ushtavaiti Gatha)
            ("https://www.sacred-texts.com/zor/sbe31/sbe3105.htm", "Gathas – Yasna 43–46 (Ushtavaiti Gatha)", 43),
            # Yasna 47–50 (Spentamainyush Gatha)
            ("https://www.sacred-texts.com/zor/sbe31/sbe3106.htm", "Gathas – Yasna 47–50 (Spentamainyush Gatha)", 47),
            # Yasna 51 (Vohu Xshathra Gatha)
            ("https://www.sacred-texts.com/zor/sbe31/sbe3107.htm", "Gathas – Yasna 51 (Vohu Xshathra Gatha)", 51),
            # Yasna 53 (Vahishtoishti Gatha)
            ("https://www.sacred-texts.com/zor/sbe31/sbe3108.htm", "Gathas – Yasna 53 (Vahishtoishti Gatha)", 53),
        ],
        "ref_fmt": "Yasna {chap}:{v}",
    },
    {
        "name":        "Vendidad",
        "id_prefix":   "Vendidad",
        "translation": "Vendidad (James Darmesteter, Sacred Books of the East Vol. 4, Public Domain)",
        "pages": [
            (f"https://www.sacred-texts.com/zor/sbe04/sbe04{n:02d}.htm",
             f"Vendidad – Fargard {n}",
             n)
            for n in range(1, 23)
        ],
        "ref_fmt": "Vendidad {chap}:{v}",
    },
]


def stable_id(prefix: str, chapter: int, verse: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"Zoroastrianism:{prefix}:{chapter}:{verse}"))


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


def clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_passages(html: str) -> list[str]:
    """Extract substantive verse/paragraph passages from a Sacred-Texts Zoroastrian page."""
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    p_blocks = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)

    passages: list[str] = []
    for block in p_blocks:
        t = clean_ws(strip_html(block))
        if len(t) < 30:
            continue
        lower = t.lower()
        if any(kw in lower for kw in [
            "sacred-texts.com", "next", "previous", "contents", "copyright",
            "footnote", "ftn", "[pg ", "p. ", "sacred books of the east"
        ]):
            continue
        passages.append(t)
    return passages


async def fetch_page(client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str) -> str:
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=30)
                if r.status_code == 200:
                    return r.text
                if r.status_code == 404:
                    return ""
            except Exception as e:
                if attempt == 2:
                    logger.warning("Failed %s — %s", url, e)
                await asyncio.sleep(2 ** attempt)
    return ""


async def ingest_text(
    client_q: QdrantClient,
    settings,
    http: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    cfg: dict,
) -> int:
    logger.info("Ingesting %s…", cfg["name"])
    grand_total = 0

    for page_entry in cfg["pages"]:
        url, book_name, chap_num = page_entry
        html = await fetch_page(http, sem, url)
        if not html:
            logger.warning("  No content for %s", book_name)
            continue

        passages = parse_passages(html)
        if not passages:
            logger.warning("  No passages for %s", book_name)
            continue

        verses = []
        for v_idx, text in enumerate(passages, start=1):
            verses.append({
                "religion":    RELIGION,
                "text":        text,
                "translation": cfg["translation"],
                "book":        book_name,
                "chapter":     chap_num,
                "verse":       v_idx,
                "reference":   cfg["ref_fmt"].format(chap=chap_num, v=v_idx),
                "source_url":  url,
            })

        for i in range(0, len(verses), BATCH_SIZE):
            batch      = verses[i : i + BATCH_SIZE]
            embeddings = await embed_texts([v["text"] for v in batch], batch_size=BATCH_SIZE)
            points = [
                PointStruct(
                    id=stable_id(cfg["id_prefix"], v["chapter"], v["verse"]),
                    vector=emb,
                    payload=v,
                )
                for v, emb in zip(batch, embeddings)
            ]
            client_q.upsert(collection_name=settings.qdrant_collection, points=points)
            grand_total += len(points)

        logger.info("  %s: %d passages", book_name, len(verses))
        await asyncio.sleep(0.5)

    logger.info("%s complete: %d passages", cfg["name"], grand_total)
    return grand_total


async def ingest_zoroastrianism():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)
    sem      = asyncio.Semaphore(3)
    grand_total = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": "CrossVerse-Ingestion/1.0"},
        follow_redirects=True,
    ) as http:
        for cfg in TEXTS:
            total = await ingest_text(client_q, settings, http, sem, cfg)
            grand_total += total

    logger.info("Zoroastrianism ingestion complete. Grand total: %d", grand_total)


if __name__ == "__main__":
    asyncio.run(ingest_zoroastrianism())
