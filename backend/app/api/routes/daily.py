from __future__ import annotations

import asyncio
import logging
import random
from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.models.schemas import DailyResponse, DailyPerspective, ScriptureChunk
from app.services.embeddings import embed_query
from app.services.rag import _search_qdrant
from app.services.scripture import build_context_block, SUPPORTED_RELIGIONS
from app.core.llm import chat_complete

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# 50 themes — picked deterministically by date
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

# Simple in-memory cache keyed by date string
_cache: Dict[str, DailyResponse] = {}

SYSTEM_PROMPT = (
    "You are a contemplative wisdom writer. Using only the scripture passages provided, "
    "write a 2-sentence daily reflection for the given tradition on the given theme. "
    "The reflection should be moving, honest, and grounded in the text. "
    "Cite the passage reference naturally within the sentences — no footnotes. "
    "Do NOT add any preamble or conclusion — just the 2 sentences."
)


async def _get_daily_perspective(
    theme: str,
    religion: str,
    query_vector: List[float],
    offset: int = 0,
) -> tuple[str, DailyPerspective]:
    chunks = await _search_qdrant(query_vector, [religion], top_k=3, offset=offset)

    if not chunks:
        return religion, DailyPerspective(
            reflection=f"No passages found in {religion} for today's theme.",
            sources=[],
        )

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

    reflection = await chat_complete(messages, temperature=0.5)
    return religion, DailyPerspective(reflection=reflection, sources=chunks)


@router.get("/daily", response_model=DailyResponse, summary="Daily scripture briefing")
async def daily_briefing(fresh: bool = False) -> DailyResponse:
    """
    Returns today's daily briefing. The theme is picked deterministically from a
    list of 50 themes using today's date as a seed. Results are cached in memory
    for the day.

    Pass ?fresh=true to bypass cache and pull a different set of verses.
    """
    try:
        today_str = date.today().isoformat()

        if not fresh and today_str in _cache:
            return _cache[today_str]

        if fresh:
            # Pick a random theme different from today's default
            day_of_year = date.today().timetuple().tm_yday
            default_idx = day_of_year % len(THEMES)
            other_indices = [i for i in range(len(THEMES)) if i != default_idx]
            theme = THEMES[random.choice(other_indices)]
            # Random offset so Qdrant returns a different page of results
            offset = random.randint(3, 30)
        else:
            day_of_year = date.today().timetuple().tm_yday
            theme = THEMES[day_of_year % len(THEMES)]
            offset = 0

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
                perspectives[religion] = DailyPerspective(
                    reflection=f"Unable to generate reflection for {religion} today.",
                    sources=[],
                )
            else:
                rel, perspective = result
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
