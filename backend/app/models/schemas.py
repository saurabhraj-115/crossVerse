from __future__ import annotations

from typing import Any, Dict, List, Optional
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

class HistoryMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    religions: Optional[List[str]] = Field(
        default=None,
        description="Filter results by religion. None means all religions.",
    )
    mode: str = Field(default="simple", pattern="^(simple|scholar|child)$")
    history: Optional[List[HistoryMessage]] = Field(
        default=None,
        description="Previous conversation turns for multi-turn context.",
    )
    language: Optional[str] = Field(
        default=None,
        description="If set, respond in this language.",
    )


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


# ---------------------------------------------------------------------------
# Situations — life wisdom from scripture
# ---------------------------------------------------------------------------

class SituationRequest(BaseModel):
    situation: str = Field(..., min_length=10, max_length=2000)
    religions: Optional[List[str]] = None


class SituationResponse(BaseModel):
    wisdom: str
    sources: List[ScriptureChunk]
    situation: str


# ---------------------------------------------------------------------------
# Fact-check
# ---------------------------------------------------------------------------

class FactCheckRequest(BaseModel):
    claim: str = Field(..., min_length=5, max_length=1000)
    religion: str


class FactCheckResponse(BaseModel):
    claim: str
    religion: str
    verdict: str  # supported | contradicted | not_found | nuanced
    explanation: str
    sources: List[ScriptureChunk]


# ---------------------------------------------------------------------------
# Ethics
# ---------------------------------------------------------------------------

class EthicsRequest(BaseModel):
    dilemma: str = Field(..., min_length=10, max_length=2000)
    religions: Optional[List[str]] = None


class EthicsPerspective(BaseModel):
    reasoning: str
    sources: List[ScriptureChunk]


class EthicsResponse(BaseModel):
    dilemma: str
    perspectives: Dict[str, str]
    sources: Dict[str, List[ScriptureChunk]]


# ---------------------------------------------------------------------------
# Daily briefing
# ---------------------------------------------------------------------------

class DailyPerspective(BaseModel):
    reflection: str
    sources: List[ScriptureChunk]


class DailyResponse(BaseModel):
    theme: str
    date: str
    perspectives: Dict[str, DailyPerspective]


# ---------------------------------------------------------------------------
# Spiritual Fingerprint
# ---------------------------------------------------------------------------

class FingerprintQuestion(BaseModel):
    id: int
    question: str
    options: List[str]


class FingerprintQuestionsResponse(BaseModel):
    questions: List[FingerprintQuestion]


class FingerprintAnswer(BaseModel):
    question_id: int
    answer: str


class FingerprintAnalyzeRequest(BaseModel):
    answers: List[FingerprintAnswer]


class FingerprintAnalyzeResponse(BaseModel):
    primary_tradition: str
    scores: Dict[str, float]
    explanation: str
    key_verses: List[ScriptureChunk]


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------

class SimilarityVerseRequest(BaseModel):
    reference: str = Field(..., min_length=2, max_length=500)
    religion: str
    top_k: int = Field(default=5, ge=1, le=20)


class SimilarityVerseResponse(BaseModel):
    reference: str
    religion: str
    similar_verses: List[ScriptureChunk]


class GraphNode(BaseModel):
    id: str
    religion: str
    reference: str
    text: str
    score: float


class GraphEdge(BaseModel):
    source: str
    target: str
    similarity: float


class SimilarityGraphRequest(BaseModel):
    concept: str = Field(..., min_length=2, max_length=500)
    religions: Optional[List[str]] = None


class SimilarityGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# ---------------------------------------------------------------------------
# Study plan
# ---------------------------------------------------------------------------

class StudyRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500)
    days: int = Field(default=7, ge=1, le=30)
    religions: Optional[List[str]] = None


class StudyDay(BaseModel):
    day: int
    theme: str
    verses: List[ScriptureChunk]
    reflection_prompt: str


class StudyResponse(BaseModel):
    topic: str
    days: List[StudyDay]


# ---------------------------------------------------------------------------
# Archaeology — conceptual lineage
# ---------------------------------------------------------------------------

class ArchaeologyRequest(BaseModel):
    concept: str = Field(..., min_length=3, max_length=500)


class ArchaeologyResponse(BaseModel):
    concept: str
    analysis: str
    sources: List[ScriptureChunk]
