"""Core RAG pipeline."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from qdrant_client.models import Filter, FieldCondition, MatchAny

from app.core.config import get_settings
from app.core.llm import chat_complete
from app.core.qdrant_client import get_qdrant
from app.models.schemas import QueryResponse, ScriptureChunk
from app.services.embeddings import embed_query
from app.services.scripture import build_context_block, payload_to_chunk

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are CrossVerse, an impartial religious-text scholar. "
    "Your ONLY job is to explain what the provided scripture passages say about the question. "
    "Rules you MUST follow:\n"
    "1. Answer ONLY using the numbered passages supplied in the context block — do not draw on outside knowledge.\n"
    "2. ALWAYS cite every claim with its reference number, e.g. [1], [3].\n"
    "3. NEVER add personal opinion, modern commentary, or theological judgement.\n"
    "4. If the passages do not address the question, say so explicitly.\n"
    "5. In Scholar mode: give detailed verse-by-verse analysis. In Simple mode: give a concise plain-English summary.\n"
)

SCHOLAR_SUFFIX = "\n\nMode: Scholar — provide detailed analysis with verse-by-verse breakdown."
SIMPLE_SUFFIX = "\n\nMode: Simple — provide a brief, plain-English summary (3-5 sentences)."


async def _search_qdrant(
    vector: List[float],
    religions: Optional[List[str]],
    top_k: int,
) -> List[ScriptureChunk]:
    settings = get_settings()
    client = get_qdrant()

    query_filter: Optional[Filter] = None
    if religions:
        normalized = [r.strip().title() for r in religions]
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="religion",
                    match=MatchAny(any=normalized),
                )
            ]
        )

    results = await client.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
    )

    chunks = []
    for hit in results:
        payload = hit.payload or {}
        chunks.append(payload_to_chunk(str(hit.id), payload, score=hit.score))
    return chunks


async def query_scriptures(
    question: str,
    religions: Optional[List[str]] = None,
    mode: str = "simple",
    history: Optional[List[Dict]] = None,
) -> QueryResponse:
    """Full RAG pipeline: embed -> search -> generate."""
    settings = get_settings()

    # 1. Embed the question
    query_vector = await embed_query(question)

    # 2. Retrieve top-k chunks
    chunks = await _search_qdrant(query_vector, religions, settings.top_k_results)

    if not chunks:
        return QueryResponse(
            answer="No scripture passages were found for this question. Please try a different query or broaden the religion filter.",
            sources=[],
            question=question,
        )

    # 3. Build context and prompt
    context = build_context_block(chunks)
    mode_suffix = SCHOLAR_SUFFIX if mode == "scholar" else SIMPLE_SUFFIX

    user_message = (
        f"Scripture passages:\n\n{context}\n\n"
        f"Question: {question}"
        f"{mode_suffix}"
    )

    # 4. Build message list with optional conversation history
    messages: List[Dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for turn in history[-10:]:  # cap at last 10 turns to avoid token overflow
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    # 5. Generate answer
    answer = await chat_complete(messages, temperature=0.2)

    return QueryResponse(
        answer=answer,
        sources=chunks,
        question=question,
    )


async def query_for_religion(
    question: str,
    religion: str,
    mode: str = "simple",
) -> QueryResponse:
    """Query restricted to a single religion — used by debate and contradiction endpoints."""
    return await query_scriptures(question, religions=[religion], mode=mode)


async def compare_religions(
    topic: str,
    religions: List[str],
) -> Dict[str, List[ScriptureChunk]]:
    """For each religion, retrieve the most relevant verses for the topic."""
    settings = get_settings()
    query_vector = await embed_query(topic)

    perspectives: Dict[str, List[ScriptureChunk]] = {}
    for religion in religions:
        chunks = await _search_qdrant(
            query_vector,
            [religion],
            top_k=4,  # fewer per religion so the UI is not overwhelming
        )
        perspectives[religion] = chunks
    return perspectives


async def find_contradictions(
    religion: str,
    topic: str,
) -> list[dict]:
    """
    Retrieve several verses on a topic within one religion and ask the LLM
    to identify apparent tensions or contradictions between them.
    """
    settings = get_settings()
    query_vector = await embed_query(topic)

    chunks = await _search_qdrant(query_vector, [religion], top_k=10)

    if len(chunks) < 2:
        return []

    context = build_context_block(chunks)
    system = (
        "You are a religious-text scholar identifying apparent tensions or contradictions "
        "between scripture passages from the SAME tradition. "
        "Use ONLY the passages provided. Always cite references. Never add opinion."
    )
    user = (
        f"Passages from {religion} on the topic '{topic}':\n\n{context}\n\n"
        "Identify up to 3 pairs of passages that appear to be in tension or to contradict each other. "
        "For each pair, output JSON with keys: verse_a_ref, verse_b_ref, explanation. "
        "Return a JSON array only, no markdown fences."
    )

    raw = await chat_complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
    )

    import json
    try:
        pairs = json.loads(raw)
    except json.JSONDecodeError:
        # Attempt to extract JSON array from raw text
        import re
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        pairs = json.loads(m.group()) if m else []

    # Enrich pairs with full chunk data
    ref_map = {c.reference: c for c in chunks}
    enriched = []
    for pair in pairs:
        enriched.append(
            {
                "verse_a": ref_map.get(pair.get("verse_a_ref", ""), {
                    "reference": pair.get("verse_a_ref", ""),
                }),
                "verse_b": ref_map.get(pair.get("verse_b_ref", ""), {
                    "reference": pair.get("verse_b_ref", ""),
                }),
                "explanation": pair.get("explanation", ""),
            }
        )
    return enriched
