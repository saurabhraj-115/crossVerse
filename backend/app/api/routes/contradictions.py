from fastapi import APIRouter, HTTPException
from app.models.schemas import ContradictionRequest, ContradictionResponse
from app.services.rag import find_contradictions
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/contradictions",
    response_model=ContradictionResponse,
    summary="Find apparent contradictions within one religion on a topic",
)
async def contradictions(request: ContradictionRequest) -> ContradictionResponse:
    """
    Retrieves multiple passages from a single religion on a topic and asks
    the LLM to identify apparent tensions or contradictions between them.
    """
    try:
        pairs = await find_contradictions(
            religion=request.religion,
            topic=request.topic,
        )
        return ContradictionResponse(
            religion=request.religion,
            topic=request.topic,
            contradictions=pairs,
        )
    except Exception as exc:
        logger.exception("Error in /contradictions: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
