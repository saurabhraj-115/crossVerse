from __future__ import annotations

import asyncio
import logging
import random
import xml.etree.ElementTree as ET
from datetime import date
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException

from app.models.schemas import DailyResponse, DailyPerspective, ScriptureChunk
from app.services.embeddings import embed_query
from app.services.rag import _search_qdrant
from app.services.scripture import build_context_block, SUPPORTED_RELIGIONS
from app.core.llm import chat_complete

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
    "You extract a single universal spiritual/ethical theme from news headlines. "
    "Return ONLY a 2-4 word lowercase phrase (e.g. 'justice and suffering', 'hope amid crisis', 'the weight of war'). "
    "No explanation, no punctuation, just the phrase."
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


async def _pick_theme_from_news() -> Optional[str]:
    """
    Fetch today's top news headlines and ask Claude to distil them into
    a single universal spiritual/ethical theme. Returns None on any failure.
    """
    try:
        headlines = await _fetch_news_headlines()
        if not headlines:
            return None

        numbered = "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines))
        messages = [
            {"role": "system", "content": THEME_PICKER_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Today's top news headlines:\n{numbered}\n\n"
                    "Identify the single most spiritually or ethically significant theme "
                    "that ALL twelve world religions could meaningfully address. "
                    "Return only the 2-4 word lowercase theme phrase."
                ),
            },
        ]
        theme = await chat_complete(messages, temperature=0.3, max_tokens=20)
        theme = theme.strip().strip('"').strip("'").lower()
        # Sanity check — reject if Claude returned a long sentence
        if theme and len(theme.split()) <= 6:
            return theme
        return None
    except Exception as e:
        logger.warning("Theme-from-news failed: %s", e)
        return None


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

    reflection = await chat_complete(messages, temperature=0.5, max_tokens=150)
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

        if fresh:
            offset = random.randint(3, 30)
            # Always try news for fresh too, but allow fallback
            theme = await _pick_theme_from_news()
            if not theme:
                day_of_year = date.today().timetuple().tm_yday
                default_idx = day_of_year % len(THEMES)
                other_indices = [i for i in range(len(THEMES)) if i != default_idx]
                theme = THEMES[random.choice(other_indices)]
        else:
            offset = 0
            theme = await _pick_theme_from_news()
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
        )

        if not fresh:
            _cache[today_str] = response
        return response

    except Exception as exc:
        logger.exception("Error in /daily: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
