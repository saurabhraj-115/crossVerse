from fastapi import APIRouter, HTTPException
from app.models.schemas import QueryRequest, QueryResponse
from app.services.rag import query_scriptures
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse, summary="Ask a question across scriptures")
async def ask_question(request: QueryRequest) -> QueryResponse:
    """
    Main RAG endpoint. Embeds the question, retrieves the most relevant
    scripture passages (optionally filtered by religion), and returns a
    grounded answer with citations.
    """
    try:
        return await query_scriptures(
            question=request.question,
            religions=request.religions,
            mode=request.mode,
        )
    except Exception as exc:
        logger.exception("Error in /query: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
