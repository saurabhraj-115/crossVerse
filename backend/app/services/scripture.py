"""Scripture utilities — payload conversion, reference parsing."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.models.schemas import ScriptureChunk

RELIGION_COLORS = {
    "Christianity": "#3B82F6",
    "Islam": "#10B981",
    "Hinduism": "#F59E0B",
    "Buddhism": "#EAB308",
    "Judaism": "#8B5CF6",
    "Sikhism": "#14B8A6",
    "Jainism": "#EA580C",
    "Zoroastrianism": "#D97706",
    "Confucianism": "#78716C",
    "Taoism": "#059669",
    "Bahai": "#9333EA",
    "Shinto": "#EC4899",
}

SUPPORTED_RELIGIONS = list(RELIGION_COLORS.keys())


def payload_to_chunk(point_id: str, payload: Dict[str, Any], score: float = 0.0) -> ScriptureChunk:
    """Convert a Qdrant point payload dict into a ScriptureChunk."""
    return ScriptureChunk(
        id=str(point_id),
        religion=payload.get("religion", ""),
        text=payload.get("text", ""),
        translation=payload.get("translation", ""),
        book=payload.get("book", ""),
        chapter=payload.get("chapter"),
        verse=payload.get("verse"),
        reference=payload.get("reference", ""),
        source_url=payload.get("source_url"),
        score=score,
    )


def chunk_to_payload(chunk: ScriptureChunk) -> Dict[str, Any]:
    """Convert a ScriptureChunk to a Qdrant-compatible payload dict."""
    return {
        "religion": chunk.religion,
        "text": chunk.text,
        "translation": chunk.translation,
        "book": chunk.book,
        "chapter": chunk.chapter,
        "verse": chunk.verse,
        "reference": chunk.reference,
        "source_url": chunk.source_url,
    }


def build_context_block(chunks: list[ScriptureChunk]) -> str:
    """Format retrieved chunks into a numbered context block for LLM prompts."""
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        lines.append(
            f"[{i}] ({chunk.religion}) {chunk.reference}\n"
            f"    Translation: {chunk.translation}\n"
            f"    \"{chunk.text}\""
        )
    return "\n\n".join(lines)
