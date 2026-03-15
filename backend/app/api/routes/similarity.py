from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    SimilarityVerseRequest,
    SimilarityVerseResponse,
    SimilarityGraphRequest,
    SimilarityGraphResponse,
    GraphNode,
    GraphEdge,
    ScriptureChunk,
)
from app.services.embeddings import embed_query, embed_texts
from app.services.rag import _search_qdrant
from app.services.scripture import SUPPORTED_RELIGIONS

logger = logging.getLogger(__name__)
router = APIRouter()


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


@router.post(
    "/similarity/verse",
    response_model=SimilarityVerseResponse,
    summary="Find cross-tradition verses similar to a given reference",
)
async def similar_verses(request: SimilarityVerseRequest) -> SimilarityVerseResponse:
    """
    Finds the verse by reference keyword search in the source religion, then
    returns semantically similar verses from other traditions.
    """
    try:
        # Embed the reference string to find similar content
        query_vector = await embed_query(request.reference)

        # Find the source verse first
        source_chunks: List[ScriptureChunk] = await _search_qdrant(
            query_vector, [request.religion], top_k=1
        )

        # Search other traditions for similar content
        other_religions = [r for r in SUPPORTED_RELIGIONS if r.lower() != request.religion.lower()]
        similar_chunks: List[ScriptureChunk] = await _search_qdrant(
            query_vector, other_religions, top_k=request.top_k
        )

        return SimilarityVerseResponse(
            reference=request.reference,
            religion=request.religion,
            similar_verses=similar_chunks,
        )

    except Exception as exc:
        logger.exception("Error in /similarity/verse: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/similarity/graph",
    response_model=SimilarityGraphResponse,
    summary="Generate similarity graph data for a concept across traditions",
)
async def similarity_graph(request: SimilarityGraphRequest) -> SimilarityGraphResponse:
    """
    Retrieves top 3 verses per religion for the concept, computes cosine similarity
    between all verse pairs, and returns graph nodes and edges.
    Only edges with similarity > 0.7 are included.
    """
    try:
        religions = request.religions or SUPPORTED_RELIGIONS
        query_vector = await embed_query(request.concept)

        # Collect all chunks with their embeddings
        all_chunks: List[Tuple[ScriptureChunk, List[float]]] = []

        for religion in religions:
            chunks = await _search_qdrant(query_vector, [religion], top_k=3)
            if not chunks:
                continue

            # Re-embed chunk texts to get their vectors for cosine similarity
            texts = [c.text for c in chunks]
            embeddings = await embed_texts(texts, batch_size=20)
            for chunk, emb in zip(chunks, embeddings):
                all_chunks.append((chunk, emb))

        # Build nodes
        nodes: List[GraphNode] = []
        for i, (chunk, _) in enumerate(all_chunks):
            nodes.append(GraphNode(
                id=f"node_{i}",
                religion=chunk.religion,
                reference=chunk.reference,
                text=chunk.text,
                score=chunk.score or 0.0,
            ))

        # Build edges (only similarity > 0.7)
        edges: List[GraphEdge] = []
        n = len(all_chunks)
        for i in range(n):
            for j in range(i + 1, n):
                chunk_i, emb_i = all_chunks[i]
                chunk_j, emb_j = all_chunks[j]

                # Skip same-religion pairs
                if chunk_i.religion == chunk_j.religion:
                    continue

                sim = _cosine_similarity(emb_i, emb_j)
                if sim > 0.7:
                    edges.append(GraphEdge(
                        source=f"node_{i}",
                        target=f"node_{j}",
                        similarity=round(sim, 4),
                    ))

        return SimilarityGraphResponse(nodes=nodes, edges=edges)

    except Exception as exc:
        logger.exception("Error in /similarity/graph: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
