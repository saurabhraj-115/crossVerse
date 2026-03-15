from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException

from app.models.schemas import ArchaeologyRequest, ArchaeologyResponse, ScriptureChunk
from app.services.embeddings import embed_query
from app.services.rag import _search_qdrant
from app.services.scripture import build_context_block
from app.core.llm import chat_complete

logger = logging.getLogger(__name__)
router = APIRouter()

SYSTEM_PROMPT = (
    "You are a scholar of comparative religion and conceptual history. "
    "Your task is to trace the conceptual lineage and parallel development of an idea across religious traditions. "
    "Rules:\n"
    "1. Use ONLY the numbered passages provided — no outside knowledge.\n"
    "2. Cite every claim with its reference number, e.g. [1], [3].\n"
    "3. Discuss: which tradition articulates the concept earliest (based on the texts given), "
    "what the shared roots or parallel expressions are, and what the key differences are.\n"
    "4. Write in flowing prose — no bullet points, no headers. Academic but accessible.\n"
    "5. If the passages do not support a conclusion, say so explicitly.\n"
)


@router.post("/archaeology", response_model=ArchaeologyResponse, summary="Trace a concept across all traditions")
async def archaeology(request: ArchaeologyRequest) -> ArchaeologyResponse:
    """
    Searches all 6 traditions for the concept and asks Claude to trace its
    conceptual lineage, shared roots, and key differences across traditions.
    """
    try:
        query_vector = await embed_query(request.concept)

        # Search across all traditions at once for breadth
        chunks: List[ScriptureChunk] = await _search_qdrant(
            query_vector,
            religions=None,  # all traditions
            top_k=18,
        )

        if not chunks:
            return ArchaeologyResponse(
                concept=request.concept,
                analysis="No relevant scripture passages were found for this concept.",
                sources=[],
            )

        context = build_context_block(chunks)
        user_message = (
            f"Scripture passages from multiple traditions:\n\n{context}\n\n"
            f"Trace the conceptual lineage and parallel development of '{request.concept}' across these traditions. "
            f"Which tradition articulates it earliest? What are the shared roots? What are the differences? "
            f"Cite every claim with passage references."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        analysis = await chat_complete(messages, temperature=0.3)

        return ArchaeologyResponse(
            concept=request.concept,
            analysis=analysis,
            sources=chunks,
        )

    except Exception as exc:
        logger.exception("Error in /archaeology: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
