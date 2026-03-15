import asyncio
from fastapi import APIRouter, HTTPException
from app.models.schemas import DebateRequest, DebateResponse
from app.services.rag import query_for_religion
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/debate", response_model=DebateResponse, summary="Multi-religion debate on a question")
async def debate(request: DebateRequest) -> DebateResponse:
    """
    Each selected religion's scriptures 'respond' to the question independently.
    Responses are generated in parallel for speed.
    """
    try:
        tasks = {
            religion: query_for_religion(
                question=request.question,
                religion=religion,
                mode="scholar",
            )
            for religion in request.religions
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        responses = {}
        for religion, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning("Debate: error for %s: %s", religion, result)
                # Return a graceful fallback rather than aborting the whole request
                from app.models.schemas import QueryResponse
                responses[religion] = QueryResponse(
                    answer=f"Unable to retrieve scripture passages for {religion} at this time.",
                    sources=[],
                    question=request.question,
                )
            else:
                responses[religion] = result

        return DebateResponse(question=request.question, responses=responses)

    except Exception as exc:
        logger.exception("Error in /debate: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
