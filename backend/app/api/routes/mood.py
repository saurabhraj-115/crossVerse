from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from fastapi import APIRouter, HTTPException

from app.models.schemas import MoodRequest, MoodResponse, ScriptureChunk
from app.services.embeddings import embed_query
from app.services.rag import _search_qdrant
from app.services.scripture import build_context_block, SUPPORTED_RELIGIONS
from app.core.llm import chat_complete

logger = logging.getLogger(__name__)
router = APIRouter()

MOOD_QUERIES: Dict[str, str] = {
    "grief": "loss death mourning comfort sorrow",
    "joy": "celebration delight happiness blessing abundance",
    "anxiety": "fear worry trust peace stillness",
    "fear": "courage protection safety divine presence",
    "hope": "hope renewal promise new beginning light",
    "loneliness": "companionship belonging community divine presence",
    "anger": "patience restraint justice",
    "gratitude": "gratitude thankfulness blessing contentment",
    "confusion": "wisdom guidance discernment clarity truth",
    "love": "love compassion kindness divine love",
}

SYSTEM_PROMPT = (
    "You are a gentle, non-preachy wisdom companion. "
    "A person is feeling {mood}. Using ONLY the provided passages, offer 3-4 sentences "
    "that meet them exactly where they are — no advice, no solutions, just the most relevant wisdom. "
    "Cite references naturally. Do not say 'the scripture says'. Speak the wisdom directly."
)


async def _search_for_tradition(
    religion: str, query_vector: List[float]
) -> List[ScriptureChunk]:
    return await _search_qdrant(query_vector, [religion], top_k=2)


@router.post("/mood", response_model=MoodResponse, summary="Scripture for your emotional state")
async def mood_scripture(request: MoodRequest) -> MoodResponse:
    """
    Searches all 6 traditions in parallel using a mood-expanded query and returns
    a warm, non-preachy wisdom message plus the source verses.
    """
    try:
        mood = request.mood
        expanded_query = MOOD_QUERIES.get(mood, mood)
        query_vector = await embed_query(expanded_query)

        tasks = [_search_for_tradition(religion, query_vector) for religion in SUPPORTED_RELIGIONS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_chunks: List[ScriptureChunk] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Mood: search error for %s: %s", SUPPORTED_RELIGIONS[i], result)
            else:
                all_chunks.extend(result)

        if not all_chunks:
            raise HTTPException(status_code=404, detail="No passages found.")

        context = build_context_block(all_chunks)
        system = SYSTEM_PROMPT.format(mood=mood)
        user_message = (
            f"The person is feeling: {mood}\n\n"
            f"Scripture passages:\n{context}\n\n"
            f"Offer 3-4 sentences of wisdom that meet them in this feeling of {mood}."
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]

        message = await chat_complete(messages, temperature=0.5)

        return MoodResponse(
            mood=mood,
            message=message,
            verses=all_chunks,
            sources=all_chunks,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in /mood: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
