from __future__ import annotations

import asyncio
import json
import logging
import re
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


@router.post("/ethics", response_model=EthicsResponse, summary="Ethical dilemma across traditions")
async def ethics_perspectives(request: EthicsRequest) -> EthicsResponse:
    """
    For each selected religion, retrieves scripture in parallel, then makes a single
    LLM call asking Claude to reason through the dilemma for all traditions at once.
    """
    try:
        religions = request.religions or SUPPORTED_RELIGIONS
        query_vector = await embed_query(request.dilemma)

        # Fetch scripture for all traditions in parallel
        tasks = [
            _search_qdrant(query_vector, [religion], top_k=6)
            for religion in religions
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        per_religion_chunks: Dict[str, List[ScriptureChunk]] = {}
        for i, result in enumerate(results):
            religion = religions[i]
            if isinstance(result, Exception):
                logger.warning("Ethics: search error for %s: %s", religion, result)
                per_religion_chunks[religion] = []
            else:
                per_religion_chunks[religion] = result

        # Build a single combined message with all tradition blocks
        tradition_blocks = []
        for religion in religions:
            chunks = per_religion_chunks[religion]
            if chunks:
                ctx = build_context_block(chunks)
                tradition_blocks.append(f"--- {religion} passages ---\n{ctx}")
            else:
                tradition_blocks.append(f"--- {religion} passages ---\n(No passages found)")

        user_msg = (
            "Ethical dilemma: " + request.dilemma + "\n\n"
            + "\n\n".join(tradition_blocks)
            + "\n\nReason through the dilemma for each tradition using ONLY its passages. "
              'Return ONLY valid JSON (no markdown) where each key is a tradition name and '
              'value is the reasoning string. '
              'Example format: {"Christianity": "...", "Islam": "..."}'
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        raw = await chat_complete(messages, temperature=0.3, max_tokens=1500)

        # Parse the JSON response
        perspectives: Dict[str, str] = {}
        try:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                parsed = json.loads(m.group(0))
                for religion in religions:
                    perspectives[religion] = parsed.get(
                        religion,
                        f"No response generated for {religion}.",
                    )
            else:
                raise ValueError("No JSON object found in LLM response")
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Ethics: JSON parse failed (%s), falling back to error messages", exc)
            for religion in religions:
                perspectives[religion] = f"Unable to parse ethics perspective for {religion}."

        sources: Dict[str, List[ScriptureChunk]] = {
            religion: per_religion_chunks.get(religion, [])
            for religion in religions
        }

        return EthicsResponse(
            dilemma=request.dilemma,
            perspectives=perspectives,
            sources=sources,
        )

    except Exception as exc:
        logger.exception("Error in /ethics: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
