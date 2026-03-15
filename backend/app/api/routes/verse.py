from fastapi import APIRouter, HTTPException
from app.core.config import get_settings
from app.core.qdrant_client import get_qdrant
from app.models.schemas import VerseResponse
from app.services.scripture import payload_to_chunk
from qdrant_client.models import Filter, FieldCondition, MatchValue
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/verse/{religion}/{ref:path}",
    response_model=VerseResponse,
    summary="Look up a specific verse by religion and reference",
)
async def get_verse(religion: str, ref: str) -> VerseResponse:
    """
    Retrieve a specific scripture verse by its religion and reference string.
    The reference should be URL-encoded if it contains slashes, e.g. 'Quran%202%3A255'.
    """
    settings = get_settings()
    client = get_qdrant()

    try:
        results, _ = await client.scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="religion", match=MatchValue(value=religion.title())),
                    FieldCondition(key="reference", match=MatchValue(value=ref)),
                ]
            ),
            limit=1,
            with_payload=True,
        )

        if not results:
            return VerseResponse(message=f"No verse found for {religion} / {ref}")

        point = results[0]
        chunk = payload_to_chunk(str(point.id), point.payload or {})
        return VerseResponse(chunk=chunk, message="ok")

    except Exception as exc:
        logger.exception("Error in /verse: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
