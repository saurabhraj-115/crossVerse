from __future__ import annotations

from openai import AsyncOpenAI
from app.core.config import get_settings
from functools import lru_cache

_client: AsyncOpenAI | None = None


def get_openai() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def get_embedding(text: str) -> list[float]:
    """Return the embedding vector for a single text string."""
    settings = get_settings()
    client = get_openai()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    return response.data[0].embedding


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Return embedding vectors for a list of texts in one API call."""
    settings = get_settings()
    client = get_openai()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    # The API returns embeddings in the same order as the input
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


async def chat_complete(messages: list[dict], temperature: float = 0.2) -> str:
    """Call chat completion and return the assistant message content."""
    settings = get_settings()
    client = get_openai()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""
