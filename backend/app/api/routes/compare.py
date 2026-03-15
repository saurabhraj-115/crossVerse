from fastapi import APIRouter, HTTPException
from app.models.schemas import CompareRequest, CompareResponse
from app.services.rag import compare_religions
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/compare", response_model=CompareResponse, summary="Compare religions on a topic")
async def compare(request: CompareRequest) -> CompareResponse:
    """
    For each requested religion, retrieve the most relevant verses about the
    given topic and return them side by side.
    """
    try:
        perspectives = await compare_religions(
            topic=request.topic,
            religions=request.religions,
        )
        return CompareResponse(topic=request.topic, perspectives=perspectives)
    except Exception as exc:
        logger.exception("Error in /compare: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
