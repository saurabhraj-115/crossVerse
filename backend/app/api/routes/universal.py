from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Dict, List

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    UniversalRequest,
    UniversalResponse,
    TraditionExpression,
    ScriptureChunk,
)
from app.services.embeddings import embed_query
from app.services.rag import _search_qdrant
from app.services.scripture import build_context_block, SUPPORTED_RELIGIONS
from app.core.llm import chat_complete

logger = logging.getLogger(__name__)
router = APIRouter()

SYSTEM_PROMPT = (
    "You are a scholar of world religions. Given verses from multiple traditions on one concept, "
    "identify the ONE universal truth they all express. "
    "Return ONLY valid JSON (no markdown): "
    '{"universal_truth": "one striking sentence", '
    '"tradition_expressions": {'
    '"Christianity": {"verse_text": "...", "reference": "...", "reflection": "..."}, '
    '"Islam": {"verse_text": "...", "reference": "...", "reflection": "..."}, '
    '"Hinduism": {"verse_text": "...", "reference": "...", "reflection": "..."}, '
    '"Buddhism": {"verse_text": "...", "reference": "...", "reflection": "..."}, '
    '"Judaism": {"verse_text": "...", "reference": "...", "reflection": "..."}, '
    '"Sikhism": {"verse_text": "...", "reference": "...", "reflection": "..."}'
    "}}. "
    "universal_truth: single sentence. "
    "reflection per tradition: 1 sentence on how that tradition uniquely expresses it. "
    "Use ONLY provided verses."
)


async def _search_for_tradition(
    religion: str, query_vector: List[float]
) -> List[ScriptureChunk]:
    return await _search_qdrant(query_vector, [religion], top_k=2)


@router.post("/universal", response_model=UniversalResponse, summary="Universal truth across traditions")
async def find_universal_truth(request: UniversalRequest) -> UniversalResponse:
    """
    Given a concept, searches all 6 traditions in parallel (top_k=2 each) and
    asks Claude to identify the single universal truth they all share.
    """
    try:
        religions = request.religions or SUPPORTED_RELIGIONS
        query_vector = await embed_query(request.concept)

        tasks = [_search_for_tradition(religion, query_vector) for religion in religions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_chunks: List[ScriptureChunk] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Universal: search error for %s: %s", religions[i], result)
            else:
                all_chunks.extend(result)

        if not all_chunks:
            raise HTTPException(status_code=404, detail="No passages found for this concept.")

        context = build_context_block(all_chunks)
        user_message = (
            f"Concept: {request.concept}\n\n"
            f"Scripture passages from all traditions:\n{context}\n\n"
            "Identify the ONE universal truth all these traditions agree on. "
            "Return ONLY valid JSON with the structure described."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        raw = await chat_complete(messages, temperature=0.3)

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise HTTPException(status_code=500, detail="Failed to parse LLM response as JSON.")

        parsed = json.loads(match.group(0))

        tradition_expressions: Dict[str, TraditionExpression] = {}
        for religion, expr in parsed.get("tradition_expressions", {}).items():
            tradition_expressions[religion] = TraditionExpression(
                verse_text=expr.get("verse_text", ""),
                reference=expr.get("reference", ""),
                reflection=expr.get("reflection", ""),
            )

        return UniversalResponse(
            concept=request.concept,
            universal_truth=parsed.get("universal_truth", ""),
            tradition_expressions=tradition_expressions,
            sources=all_chunks,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in /universal: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
