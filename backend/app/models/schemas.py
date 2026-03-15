from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Core scripture chunk — stored in Qdrant payload and returned in responses
# ---------------------------------------------------------------------------

class ScriptureChunk(BaseModel):
    id: str
    religion: str  # "Christianity" | "Islam" | "Hinduism" | "Buddhism" | "Judaism" | "Sikhism"
    text: str
    translation: str
    book: str
    chapter: Optional[int] = None
    verse: Optional[int] = None
    reference: str  # e.g. "Genesis 1:1", "Quran 2:255", "Gita 2:47"
    source_url: Optional[str] = None
    score: Optional[float] = None  # similarity score when returned from search


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    religions: Optional[List[str]] = Field(
        default=None,
        description="Filter results by religion. None means all religions.",
    )
    mode: str = Field(default="simple", pattern="^(simple|scholar)$")


class QueryResponse(BaseModel):
    answer: str
    sources: List[ScriptureChunk]
    question: str


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------

class CompareRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=500)
    religions: List[str] = Field(..., min_length=2)


class CompareResponse(BaseModel):
    topic: str
    perspectives: Dict[str, List[ScriptureChunk]]  # religion -> verses


# ---------------------------------------------------------------------------
# Contradictions
# ---------------------------------------------------------------------------

class ContradictionRequest(BaseModel):
    religion: str
    topic: str = Field(..., min_length=2, max_length=500)


class ContradictionResponse(BaseModel):
    religion: str
    topic: str
    contradictions: List[Dict]  # list of {"verse_a": ScriptureChunk, "verse_b": ScriptureChunk, "explanation": str}


# ---------------------------------------------------------------------------
# Verse lookup
# ---------------------------------------------------------------------------

class VerseResponse(BaseModel):
    chunk: Optional[ScriptureChunk] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Debate
# ---------------------------------------------------------------------------

class DebateRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    religions: List[str] = Field(..., min_length=2)


class DebateResponse(BaseModel):
    question: str
    responses: Dict[str, QueryResponse]  # religion -> response


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------

class TopicCategory(BaseModel):
    name: str
    topics: List[str]


class TopicsResponse(BaseModel):
    categories: List[TopicCategory]
