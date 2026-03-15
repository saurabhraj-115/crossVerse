from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.models.schemas import StudyRequest, StudyResponse, StudyDay, ScriptureChunk
from app.services.embeddings import embed_query
from app.services.rag import _search_qdrant
from app.services.scripture import build_context_block, SUPPORTED_RELIGIONS
from app.core.llm import chat_complete

logger = logging.getLogger(__name__)
router = APIRouter()

PLAN_SYSTEM_PROMPT = (
    "You are a curriculum designer for comparative religious studies. "
    "Given a topic and number of days, generate a structured study plan with one sub-theme per day. "
    "Return ONLY valid JSON — no markdown, no extra text — in this exact format:\n"
    '[{"day": 1, "theme": "Sub-theme title", "reflection_prompt": "A question to reflect on..."}, ...]\n'
    "Each day must have: day (int), theme (short descriptive title), reflection_prompt (one thought-provoking question). "
    "Make the sub-themes progress logically from foundational to advanced."
)

VERSE_SYSTEM_PROMPT = (
    "You are a contemplative religious educator. "
    "You will be given the study day theme and relevant scripture passages. "
    "Write ONE reflection prompt question (1 sentence) that invites deep engagement with the theme using the passages. "
    "Return only the question — no preamble, no quotation marks."
)


async def _generate_study_plan_outline(topic: str, days: int) -> List[dict]:
    """Ask Claude to generate the day-by-day outline."""
    user_message = (
        f"Topic: {topic}\nDays: {days}\n\n"
        f"Generate a {days}-day comparative religious study plan on the topic '{topic}'. "
        f"Each day should have a focused sub-theme and a reflection prompt."
    )

    messages = [
        {"role": "system", "content": PLAN_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    raw = await chat_complete(messages, temperature=0.4)

    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        raise ValueError("LLM did not return valid JSON array for study plan")

    return json.loads(m.group())


async def _get_day_verses(theme: str, religions: List[str]) -> List[ScriptureChunk]:
    """Retrieve 2-3 verses per religion for the given theme."""
    query_vector = await embed_query(theme)
    tasks = [_search_qdrant(query_vector, [r], top_k=2) for r in religions]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_chunks: List[ScriptureChunk] = []
    for result in results:
        if isinstance(result, Exception):
            continue
        all_chunks.extend(result)
    return all_chunks


@router.post("/study", response_model=StudyResponse, summary="Generate multi-day scripture study plan")
async def generate_study_plan(request: StudyRequest) -> StudyResponse:
    """
    Generates a structured multi-day study plan for a given topic.
    For each day: a sub-theme, 2-3 verses per tradition, and a reflection prompt.
    """
    try:
        religions = request.religions or SUPPORTED_RELIGIONS

        # 1. Get outline from Claude
        outline = await _generate_study_plan_outline(request.topic, request.days)

        # 2. For each day, fetch verses
        study_days: List[StudyDay] = []
        for entry in outline[: request.days]:
            day_num = entry.get("day", 1)
            theme = entry.get("theme", f"Day {day_num}")
            reflection_prompt = entry.get("reflection_prompt", "")

            verses = await _get_day_verses(theme, religions)

            study_days.append(StudyDay(
                day=day_num,
                theme=theme,
                verses=verses,
                reflection_prompt=reflection_prompt,
            ))

        return StudyResponse(topic=request.topic, days=study_days)

    except Exception as exc:
        logger.exception("Error in /study: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
