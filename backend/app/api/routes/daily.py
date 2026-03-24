from __future__ import annotations

import asyncio
import json
import logging
import random
import xml.etree.ElementTree as ET
from datetime import date
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import DailyResponse, DailyPerspective, ScriptureChunk
from app.services.embeddings import embed_query
from app.services.rag import _search_qdrant
from app.services.scripture import build_context_block, SUPPORTED_RELIGIONS
from app.core.llm import chat_complete, HAIKU

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Fallback themes — used when news fetch fails
# ---------------------------------------------------------------------------
THEMES = [
    "gratitude", "forgiveness", "compassion", "wisdom", "suffering",
    "love", "death", "hope", "prayer", "silence",
    "humility", "courage", "justice", "truth", "mercy",
    "faith", "doubt", "joy", "grief", "service",
    "community", "solitude", "temptation", "redemption", "peace",
    "anger", "patience", "generosity", "ego", "surrender",
    "sacred texts", "the soul", "nature and creation", "free will", "destiny",
    "wealth and poverty", "family", "war and peace", "healing", "light and darkness",
    "sin and guilt", "salvation", "mindfulness", "karma", "divine presence",
    "pilgrimage", "fasting", "sacrifice", "ritual", "afterlife",
]

# News RSS feeds — tried in order until one succeeds
NEWS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://feeds.reuters.com/reuters/topNews",
]

# Simple in-memory cache keyed by date string
_cache: Dict[str, DailyResponse] = {}

SYSTEM_PROMPT = (
    "You are a contemplative wisdom writer. Using only the scripture passages provided, "
    "write a 2-sentence daily reflection for the given tradition on the given theme. "
    "The reflection should be moving, honest, and grounded in the text. "
    "Cite the passage reference naturally within the sentences — no footnotes. "
    "Do NOT add any preamble or conclusion — just the 2 sentences. "
    "CRITICAL: You MUST always write the 2 sentences. Never refuse or explain why you cannot. "
    "If the passages do not perfectly match the theme, find the closest connection and write the reflection anyway."
)

THEME_PICKER_SYSTEM = (
    "You are a spiritual theme extractor. Given news headlines, you pick the single most "
    "ethically or spiritually rich headline and derive a universal theme directly from it. "
    "Reply with EXACTLY two lines — nothing else:\n"
    "LINE1: the exact verbatim headline you chose (copy it word-for-word)\n"
    "LINE2: a 2-4 word lowercase spiritual theme that directly captures what that headline is about "
    "(e.g. if the headline is about a famine → 'hunger and compassion'; "
    "if it is about a ceasefire → 'peace after conflict')"
)


async def _fetch_news_headlines() -> List[str]:
    """Fetch top headlines from a news RSS feed. Returns up to 8 headlines."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CrossVerse/1.0)"}
    async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
        for feed_url in NEWS_FEEDS:
            try:
                resp = await client.get(feed_url, headers=headers)
                if resp.status_code != 200:
                    continue
                root = ET.fromstring(resp.text)
                headlines = []
                for item in root.findall(".//item"):
                    title = item.find("title")
                    if title is not None and title.text:
                        text = title.text.strip()
                        if text and len(text) > 10:
                            headlines.append(text)
                    if len(headlines) >= 8:
                        break
                if headlines:
                    return headlines
            except Exception as e:
                logger.debug("Feed %s failed: %s", feed_url, e)
                continue
    return []


async def _pick_theme_from_news() -> tuple[Optional[str], Optional[str]]:
    """
    Fetch today's top news headlines and ask Claude to distil them into
    a single universal spiritual/ethical theme.
    Returns (theme, source_headline) or (None, None) on failure.
    """
    try:
        headlines = await _fetch_news_headlines()
        if not headlines:
            return None, None

        numbered = "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines))
        messages = [
            {"role": "system", "content": THEME_PICKER_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Today's top news headlines:\n{numbered}\n\n"
                    "Pick the headline richest in spiritual or ethical meaning. "
                    "Return exactly two lines as instructed."
                ),
            },
        ]
        raw = await chat_complete(messages, temperature=0.2, max_tokens=80, model=HAIKU)
        lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
        if len(lines) < 2:
            return None, None
        source_headline = lines[0].strip('"').strip("'")
        theme = lines[1].strip('"').strip("'").lower()
        # Validate: theme must be short, headline must look like a real headline
        if theme and len(theme.split()) <= 6 and len(source_headline) > 10:
            return theme, source_headline
        return None, None
    except Exception as e:
        logger.warning("Theme-from-news failed: %s", e)
        return None, None


async def _get_daily_perspective(
    theme: str,
    religion: str,
    query_vector: List[float],
    offset: int = 0,
) -> tuple[str, Optional[DailyPerspective]]:
    chunks = await _search_qdrant(query_vector, [religion], top_k=3, offset=offset)

    if not chunks:
        return religion, None

    context = build_context_block(chunks)
    user_message = (
        f"Tradition: {religion}\nTheme: {theme}\n\n"
        f"Scripture passages:\n{context}\n\n"
        f"Write a 2-sentence daily reflection for the {religion} tradition on the theme of {theme}. "
        f"Ground it in the passages above and cite references naturally."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    reflection = await chat_complete(messages, temperature=0.5, max_tokens=150, model=HAIKU)
    return religion, DailyPerspective(reflection=reflection, sources=chunks)


@router.get("/daily", response_model=DailyResponse, summary="Daily scripture briefing")
async def daily_briefing(fresh: bool = False) -> DailyResponse:
    """
    Returns today's daily briefing. The theme is derived from today's top
    news headlines — Claude distils them into a universal spiritual/ethical
    theme, then all 12 traditions reflect on it. Falls back to a curated
    theme list if the news fetch fails.

    Pass ?fresh=true to bypass cache and regenerate.
    """
    try:
        today_str = date.today().isoformat()

        if not fresh and today_str in _cache:
            return _cache[today_str]

        headline: Optional[str] = None
        if fresh:
            offset = random.randint(3, 30)
            theme, headline = await _pick_theme_from_news()
            if not theme:
                day_of_year = date.today().timetuple().tm_yday
                default_idx = day_of_year % len(THEMES)
                other_indices = [i for i in range(len(THEMES)) if i != default_idx]
                theme = THEMES[random.choice(other_indices)]
        else:
            offset = 0
            theme, headline = await _pick_theme_from_news()
            if not theme:
                import hashlib
                seed = int(hashlib.md5(today_str.encode()).hexdigest(), 16)
                theme = THEMES[seed % len(THEMES)]

        query_vector = await embed_query(theme)

        tasks = [
            _get_daily_perspective(theme, religion, query_vector, offset)
            for religion in SUPPORTED_RELIGIONS
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        perspectives: Dict[str, DailyPerspective] = {}
        for i, result in enumerate(results):
            religion = SUPPORTED_RELIGIONS[i]
            if isinstance(result, Exception):
                logger.warning("Daily: error for %s: %s", religion, result)
            else:
                rel, perspective = result
                if perspective is not None:
                    perspectives[rel] = perspective

        response = DailyResponse(
            theme=theme,
            date=today_str,
            perspectives=perspectives,
            headline=headline,
        )

        if not fresh:
            _cache[today_str] = response
        return response

    except Exception as exc:
        logger.exception("Error in /daily: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.get("/daily/stream", summary="Daily scripture briefing (SSE streaming)")
async def daily_briefing_stream(fresh: bool = False):
    """
    Server-Sent Events version of /daily.
    Emits events as each tradition completes so the UI can render cards
    progressively instead of waiting for all 12 LLM calls to finish.

    Event types:
      {"type": "theme",  "theme": str, "date": str, "headline": str|null}
      {"type": "card",   "religion": str, "perspective": {...}}
      {"type": "done"}
      {"type": "error",  "message": str}
    """
    today_str = date.today().isoformat()

    # ── Cache hit: stream stored data immediately ──────────────────────────
    if not fresh and today_str in _cache:
        cached = _cache[today_str]

        async def _stream_cached():
            yield _sse({"type": "theme", "theme": cached.theme,
                        "date": cached.date, "headline": cached.headline})
            for religion, perspective in cached.perspectives.items():
                yield _sse({"type": "card", "religion": religion,
                            "perspective": perspective.dict()})
                await asyncio.sleep(0)
            yield _sse({"type": "done"})

        return StreamingResponse(
            _stream_cached(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ── Live generation: stream each card as it arrives ───────────────────
    async def _stream_live():
        try:
            headline: Optional[str] = None
            if fresh:
                offset = random.randint(3, 30)
                theme, headline = await _pick_theme_from_news()
                if not theme:
                    day_of_year = date.today().timetuple().tm_yday
                    default_idx = day_of_year % len(THEMES)
                    other_indices = [i for i in range(len(THEMES)) if i != default_idx]
                    theme = THEMES[random.choice(other_indices)]
            else:
                offset = 0
                theme, headline = await _pick_theme_from_news()
                if not theme:
                    import hashlib
                    seed = int(hashlib.md5(today_str.encode()).hexdigest(), 16)
                    theme = THEMES[seed % len(THEMES)]

            # Emit theme immediately — unblocks the UI header
            yield _sse({"type": "theme", "theme": theme,
                        "date": today_str, "headline": headline})

            query_vector = await embed_query(theme)

            # Fan-out: each tradition pushes its result into a queue as it finishes
            queue: asyncio.Queue = asyncio.Queue()

            async def _fetch_one(religion: str) -> None:
                try:
                    rel, perspective = await _get_daily_perspective(
                        theme, religion, query_vector, offset
                    )
                    await queue.put((rel, perspective))
                except Exception as e:
                    logger.warning("Stream: error for %s: %s", religion, e)
                    await queue.put((religion, None))

            tasks = [asyncio.create_task(_fetch_one(r)) for r in SUPPORTED_RELIGIONS]

            collected: Dict[str, DailyPerspective] = {}
            for _ in SUPPORTED_RELIGIONS:
                religion, perspective = await queue.get()
                if perspective is not None:
                    collected[religion] = perspective
                    yield _sse({"type": "card", "religion": religion,
                                "perspective": perspective.dict()})

            yield _sse({"type": "done"})

            # Populate the date cache so subsequent loads are instant
            if not fresh:
                _cache[today_str] = DailyResponse(
                    theme=theme,
                    date=today_str,
                    perspectives=collected,
                    headline=headline,
                )

        except Exception as exc:
            logger.exception("Error in /daily/stream: %s", exc)
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        _stream_live(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
