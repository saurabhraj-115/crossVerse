"""Embedding service — wraps OpenAI embeddings with batching and retry."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from openai import RateLimitError, APIConnectionError

from app.core.config import get_settings
from app.core.llm import get_openai

logger = logging.getLogger(__name__)


@retry(
    retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
)
async def _embed_batch(texts: List[str]) -> List[List[float]]:
    settings = get_settings()
    client = get_openai()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


async def embed_texts(texts: List[str], batch_size: int = 20) -> List[List[float]]:
    """Embed a list of texts using batched OpenAI calls."""
    all_embeddings: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = await _embed_batch(batch)
        all_embeddings.extend(embeddings)
        if i + batch_size < len(texts):
            await asyncio.sleep(0.1)  # gentle rate-limit buffer
    return all_embeddings


async def embed_query(text: str) -> List[float]:
    """Embed a single query string."""
    results = await _embed_batch([text])
    return results[0]
