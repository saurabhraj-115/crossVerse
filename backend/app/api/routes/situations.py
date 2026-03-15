from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.models.schemas import SituationRequest, SituationResponse, ScriptureChunk
from app.services.embeddings import embed_query
from app.services.rag import _search_qdrant
from app.services.scripture import build_context_block
from app.core.llm import chat_complete

logger = logging.getLogger(__name__)
router = APIRouter()

SYSTEM_PROMPT = (
    "You are a compassionate wisdom guide drawing only from sacred scripture. "
    "Your job is to offer honest, grounded human wisdom for someone going through a difficult time. "
    "Rules you MUST follow:\n"
    "1. Use ONLY the numbered passages supplied in the context block.\n"
    "2. Cite every claim with its reference number, e.g. [1], [3].\n"
    "3. Do NOT sound preachy, religious, or lecture-like. Sound like a wise, caring friend.\n"
    "4. Do NOT say 'the scripture says' or 'God commands'. Speak the wisdom directly.\n"
    "5. If passages do not address the situation, say so honestly.\n"
)


@router.post("/situations", response_model=SituationResponse, summary="Life wisdom from scripture")
async def get_situation_wisdom(request: SituationRequest) -> SituationResponse:
    """
    Embeds the situation, retrieves relevant scripture passages, and asks Claude
    to synthesize human wisdom in a warm, non-preachy tone.
    """
    try:
        query_vector = await embed_query(request.situation)
        chunks: List[ScriptureChunk] = await _search_qdrant(
            query_vector,
            request.religions,
            top_k=12,
        )

        if not chunks:
            return SituationResponse(
                wisdom="No relevant scripture passages were found for this situation. Please try describing it differently.",
                sources=[],
                situation=request.situation,
            )

        context = build_context_block(chunks)
        user_message = (
            f"Scripture passages:\n\n{context}\n\n"
            f"The user is going through a difficult life situation. "
            f"Provide human wisdom from scripture — not preachy, not religious-sounding, just honest wisdom. "
            f"The user said: {request.situation}. "
            f"Use ONLY the retrieved passages, cite every claim."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        wisdom = await chat_complete(messages, temperature=0.4)

        return SituationResponse(
            wisdom=wisdom,
            sources=chunks,
            situation=request.situation,
        )

    except Exception as exc:
        logger.exception("Error in /situations: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
