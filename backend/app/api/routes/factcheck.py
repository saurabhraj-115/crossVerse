from __future__ import annotations

import logging
import re
from typing import List

from fastapi import APIRouter, HTTPException

from app.models.schemas import FactCheckRequest, FactCheckResponse, ScriptureChunk
from app.services.embeddings import embed_query
from app.services.rag import _search_qdrant
from app.services.scripture import build_context_block
from app.core.llm import chat_complete

logger = logging.getLogger(__name__)
router = APIRouter()

SYSTEM_PROMPT = (
    "You are a precise religious-text fact-checker. "
    "Given scripture passages from one tradition and a claim, determine whether the tradition's "
    "scripture supports, contradicts, does not address, or gives a nuanced answer on the claim. "
    "Rules:\n"
    "1. Use ONLY the numbered passages provided.\n"
    "2. Cite every claim with its reference number, e.g. [1], [3].\n"
    "3. Begin your response with one of these exact verdict tokens on its own line: "
    "VERDICT: supported | VERDICT: contradicted | VERDICT: not_found | VERDICT: nuanced\n"
    "4. Then provide a precise explanation citing exact passages.\n"
)

VERDICT_PATTERN = re.compile(
    r"VERDICT:\s*(supported|contradicted|not_found|nuanced)", re.IGNORECASE
)


@router.post("/factcheck", response_model=FactCheckResponse, summary="Fact-check a claim against scripture")
async def fact_check(request: FactCheckRequest) -> FactCheckResponse:
    """
    Embeds the claim, searches Qdrant filtered by religion, and asks Claude to
    verify whether the claim is supported, contradicted, not addressed, or nuanced.
    """
    try:
        query_vector = await embed_query(request.claim)
        chunks: List[ScriptureChunk] = await _search_qdrant(
            query_vector,
            [request.religion],
            top_k=10,
        )

        if not chunks:
            return FactCheckResponse(
                claim=request.claim,
                religion=request.religion,
                verdict="not_found",
                explanation=f"No relevant scripture passages from {request.religion} were found for this claim.",
                sources=[],
            )

        context = build_context_block(chunks)
        user_message = (
            f"Scripture passages from {request.religion}:\n\n{context}\n\n"
            f"Does {request.religion}'s scripture support, contradict, or not address this claim? "
            f"Be precise. Claim: {request.claim}. Cite exact passages."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        raw = await chat_complete(messages, temperature=0.2)

        # Extract verdict token
        m = VERDICT_PATTERN.search(raw)
        verdict = m.group(1).lower() if m else "nuanced"

        # Remove the VERDICT line from explanation
        explanation = VERDICT_PATTERN.sub("", raw).strip()

        return FactCheckResponse(
            claim=request.claim,
            religion=request.religion,
            verdict=verdict,
            explanation=explanation,
            sources=chunks,
        )

    except Exception as exc:
        logger.exception("Error in /factcheck: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
