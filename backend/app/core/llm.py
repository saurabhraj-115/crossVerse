from __future__ import annotations

import anthropic
from openai import AsyncOpenAI
from app.core.config import get_settings

_openai_client: AsyncOpenAI | None = None
_anthropic_client: anthropic.AsyncAnthropic | None = None


def get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        settings = get_settings()
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


def get_anthropic() -> anthropic.AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        settings = get_settings()
        _anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


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
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


# Model tiers — import these in route files
SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"


async def chat_complete(
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 2048,
    model: str | None = None,
) -> str:
    """Call Claude and return the assistant message content."""
    settings = get_settings()
    client = get_anthropic()

    system_prompt = ""
    conversation = []
    for msg in messages:
        if msg["role"] == "system":
            system_prompt = msg["content"]
        else:
            conversation.append({"role": msg["role"], "content": msg["content"]})

    response = await client.messages.create(
        model=model or settings.llm_model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=conversation,
    )
    return response.content[0].text
