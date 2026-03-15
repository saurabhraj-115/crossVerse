from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.models.schemas import EthicsRequest, EthicsResponse, ScriptureChunk
from app.services.embeddings import embed_query
from app.services.rag import _search_qdrant
from app.services.scripture import build_context_block, SUPPORTED_RELIGIONS
from app.core.llm import chat_complete

logger = logging.getLogger(__name__)
router = APIRouter()

SYSTEM_PROMPT = (
    "You are a religious-text scholar reasoning through ethical dilemmas using only scripture. "
    "Rules:\n"
    "1. Use ONLY the numbered passages provided — no outside knowledge.\n"
    "2. Cite every claim with its reference number, e.g. [1], [3].\n"
    "3. Show how the tradition reasons through the dilemma — not just what it forbids or allows.\n"
    "4. Be balanced and accurate. Do not editorialize.\n"
    "5. If passages do not address the dilemma, say so explicitly.\n"
)


async def _get_ethics_perspective(
    dilemma: str,
    religion: str,
    query_vector: List[float],
) -> tuple[str, str, List[ScriptureChunk]]:
    """Retrieve and generate ethics perspective for one religion."""
    chunks = await _search_qdrant(query_vector, [religion], top_k=6)

    if not chunks:
        return religion, f"No relevant scripture passages from {religion} found for this dilemma.", []

    context = build_context_block(chunks)
    user_message = (
        f"Scripture passages from {religion}:\n\n{context}\n\n"
        f"How does {religion} scripture reason through this ethical dilemma? "
        f"Use ONLY provided passages, cite every claim. "
        f"Dilemma: {dilemma}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    reasoning = await chat_complete(messages, temperature=0.3)
    return religion, reasoning, chunks


@router.post("/ethics", response_model=EthicsResponse, summary="Ethical dilemma across traditions")
async def ethics_perspectives(request: EthicsRequest) -> EthicsResponse:
    """
    For each selected religion, retrieves scripture and asks Claude to reason
    through the ethical dilemma. All religions are queried in parallel.
    """
    try:
        religions = request.religions or SUPPORTED_RELIGIONS
        query_vector = await embed_query(request.dilemma)

        tasks = [
            _get_ethics_perspective(request.dilemma, religion, query_vector)
            for religion in religions
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        perspectives: Dict[str, str] = {}
        sources: Dict[str, List[ScriptureChunk]] = {}

        for i, result in enumerate(results):
            religion = religions[i]
            if isinstance(result, Exception):
                logger.warning("Ethics: error for %s: %s", religion, result)
                perspectives[religion] = f"Unable to retrieve ethics perspective for {religion} at this time."
                sources[religion] = []
            else:
                rel, reasoning, chunks = result
                perspectives[rel] = reasoning
                sources[rel] = chunks

        return EthicsResponse(
            dilemma=request.dilemma,
            perspectives=perspectives,
            sources=sources,
        )

    except Exception as exc:
        logger.exception("Error in /ethics: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
