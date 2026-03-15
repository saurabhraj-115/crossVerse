from __future__ import annotations

import json
import logging
import re
from typing import List

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    FingerprintQuestion,
    FingerprintQuestionsResponse,
    FingerprintAnalyzeRequest,
    FingerprintAnalyzeResponse,
    ScriptureChunk,
)
from app.services.embeddings import embed_query
from app.services.rag import _search_qdrant
from app.core.llm import chat_complete
from app.services.scripture import SUPPORTED_RELIGIONS

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Hardcoded quiz questions
# ---------------------------------------------------------------------------
QUESTIONS: List[FingerprintQuestion] = [
    FingerprintQuestion(
        id=1,
        question="What happens after we die?",
        options=[
            "We are resurrected and judged by God",
            "Our soul is reborn in a new body (reincarnation)",
            "We enter a state of non-self (nirvana/cessation)",
            "We return to the collective divine consciousness",
        ],
    ),
    FingerprintQuestion(
        id=2,
        question="Why does suffering exist in the world?",
        options=[
            "It is a test from God to strengthen our faith",
            "It arises from attachment and ignorance",
            "It is the result of past karma",
            "It is part of God's inscrutable divine plan",
        ],
    ),
    FingerprintQuestion(
        id=3,
        question="Do human beings have free will?",
        options=[
            "Yes — God gave us free will and we are accountable for our choices",
            "Partly — divine grace is needed for righteous action",
            "Free will is an illusion; all events unfold according to dharma",
            "Our choices matter, but they operate within karma and cosmic law",
        ],
    ),
    FingerprintQuestion(
        id=4,
        question="When duty and personal desire conflict, what should guide you?",
        options=[
            "Duty to God and community must come first",
            "Personal desire, if it harms no one, is valid",
            "Duty (dharma) is paramount — desire is a distraction",
            "Detachment from both — act without attachment to outcome",
        ],
    ),
    FingerprintQuestion(
        id=5,
        question="What is the nature of God or the divine?",
        options=[
            "A personal God — singular, all-knowing, all-powerful",
            "An impersonal ultimate reality (Brahman) underlying all things",
            "The divine is within all beings equally",
            "There is no creator God; liberation is found within",
        ],
    ),
    FingerprintQuestion(
        id=6,
        question="What is the purpose of prayer or meditation?",
        options=[
            "To communicate with and seek guidance from God",
            "To cultivate inner stillness and clear the mind",
            "To align the self with divine will and cosmic order",
            "To dissolve the ego and realize unity with the divine",
        ],
    ),
    FingerprintQuestion(
        id=7,
        question="What does genuine forgiveness look like?",
        options=[
            "Forgiving others as God forgives us — unconditionally",
            "Releasing resentment to free ourselves from suffering",
            "Recognizing that wrongdoers are bound by their own karma",
            "Compassion for the ignorance that caused the harm",
        ],
    ),
    FingerprintQuestion(
        id=8,
        question="Do you believe in reincarnation?",
        options=[
            "No — each soul lives once and is then judged",
            "Yes — the soul cycles through births until liberation",
            "The cycle of rebirth is the central problem to escape",
            "The self that reincarnates is itself an illusion",
        ],
    ),
    FingerprintQuestion(
        id=9,
        question="How do you relate to scripture and holy texts?",
        options=[
            "Scripture is the literal or inspired word of God",
            "Scripture is a guide, but reason and experience also matter",
            "Scripture points to truth, but direct experience is primary",
            "All authentic scriptures point to the same underlying truth",
        ],
    ),
    FingerprintQuestion(
        id=10,
        question="What is the path to liberation, salvation, or ultimate freedom?",
        options=[
            "Faith, repentance, and grace from God",
            "Righteous action, devotion, and knowledge (the three paths)",
            "Letting go of all attachment through the Eightfold Path",
            "Selfless service and surrender to God's will (seva/bhakti)",
        ],
    ),
]

SYSTEM_PROMPT = (
    "You are a religious studies scholar. You will be given a person's answers to 10 philosophical questions. "
    "Analyze how well their worldview aligns with each of the six traditions: "
    "Christianity, Islam, Hinduism, Buddhism, Judaism, Sikhism.\n"
    "Return ONLY valid JSON in this exact format — no markdown fences, no extra text:\n"
    '{"primary_tradition": "...", "scores": {"Christianity": 0.0, "Islam": 0.0, "Hinduism": 0.0, '
    '"Buddhism": 0.0, "Judaism": 0.0, "Sikhism": 0.0}, '
    '"explanation": "..."}\n'
    "Scores must be floats between 0.0 and 1.0. "
    "primary_tradition must be one of: Christianity, Islam, Hinduism, Buddhism, Judaism, Sikhism. "
    "explanation should be 3-4 sentences explaining the primary match and key nuances."
)


@router.get(
    "/fingerprint/questions",
    response_model=FingerprintQuestionsResponse,
    summary="Get spiritual fingerprint quiz questions",
)
async def get_questions() -> FingerprintQuestionsResponse:
    """Returns the 10 fixed quiz questions with 4 options each."""
    return FingerprintQuestionsResponse(questions=QUESTIONS)


@router.post(
    "/fingerprint/analyze",
    response_model=FingerprintAnalyzeResponse,
    summary="Analyze spiritual fingerprint from quiz answers",
)
async def analyze_fingerprint(request: FingerprintAnalyzeRequest) -> FingerprintAnalyzeResponse:
    """
    Analyzes the user's answers against each tradition's worldview using Claude,
    then fetches 3 key verses for the primary tradition.
    """
    try:
        # Build Q&A text for Claude
        question_map = {q.id: q for q in QUESTIONS}
        qa_lines = []
        for ans in request.answers:
            q = question_map.get(ans.question_id)
            if q:
                qa_lines.append(f"Q{ans.question_id}: {q.question}\nAnswer: {ans.answer}")

        qa_text = "\n\n".join(qa_lines)

        user_message = (
            f"Here are the person's answers to 10 philosophical questions:\n\n{qa_text}\n\n"
            f"Analyze how their worldview aligns with each of the six religious traditions and return JSON."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        raw = await chat_complete(messages, temperature=0.2)

        # Parse JSON response
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise ValueError("LLM did not return valid JSON")

        data = json.loads(m.group())
        primary = data.get("primary_tradition", "Christianity")
        scores = data.get("scores", {r: 0.0 for r in SUPPORTED_RELIGIONS})
        explanation = data.get("explanation", "")

        # Fetch 3 key verses for the primary tradition
        query_vector = await embed_query(f"spiritual path liberation salvation {primary}")
        key_verses: List[ScriptureChunk] = await _search_qdrant(
            query_vector, [primary], top_k=3
        )

        return FingerprintAnalyzeResponse(
            primary_tradition=primary,
            scores=scores,
            explanation=explanation,
            key_verses=key_verses,
        )

    except Exception as exc:
        logger.exception("Error in /fingerprint/analyze: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
