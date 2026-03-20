from __future__ import annotations

from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
)
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)

_sync_client: QdrantClient | None = None
_async_client: AsyncQdrantClient | None = None


def _client_kwargs() -> dict:
    """Return kwargs for QdrantClient — URL if set, otherwise host+port."""
    settings = get_settings()
    if settings.qdrant_url:
        kwargs: dict = {"url": settings.qdrant_url, "timeout": 30, "prefer_grpc": False}
        if settings.qdrant_api_key:
            kwargs["api_key"] = settings.qdrant_api_key
        return kwargs
    return {"host": settings.qdrant_host, "port": settings.qdrant_port, "timeout": 30, "prefer_grpc": False}


def get_qdrant_sync() -> QdrantClient:
    global _sync_client
    if _sync_client is None:
        _sync_client = QdrantClient(**_client_kwargs())
    return _sync_client


def get_qdrant() -> AsyncQdrantClient:
    global _async_client
    if _async_client is None:
        _async_client = AsyncQdrantClient(**_client_kwargs())
    return _async_client


async def ensure_collection_exists() -> None:
    """Create the scriptures collection if it doesn't already exist."""
    settings = get_settings()
    client = get_qdrant()

    try:
        collections = await client.get_collections()
        existing = {c.name for c in collections.collections}

        if settings.qdrant_collection not in existing:
            await client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )
            # Create payload indexes for fast filtering
            await client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name="religion",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            await client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name="book",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.info(
                "Created Qdrant collection '%s'", settings.qdrant_collection
            )
        else:
            logger.info(
                "Qdrant collection '%s' already exists", settings.qdrant_collection
            )
    except Exception as exc:
        logger.warning("Could not verify Qdrant collection: %s", exc)
