from __future__ import annotations

import json

import httpx
import pytest

from cortex.embeddings.gemini import GeminiEmbeddingError, GeminiEmbeddingProvider


async def test_gemini_provider_calls_embed_content_without_leaking_key() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["api_key"] = request.headers.get("x-goog-api-key")
        seen["payload"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={"embedding": {"values": [0.1, -0.2, 0.3]}},
        )

    provider = GeminiEmbeddingProvider(
        api_key="test-key",
        model="gemini-embedding-001",
        dimensions=3,
        version="gemini-test-v1",
        transport=httpx.MockTransport(handler),
    )

    output = await provider.embed("sha256:input", "hello from slack")

    assert output.vector == [0.1, -0.2, 0.3]
    assert output.vector_hash.startswith("sha256:")
    assert seen["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-embedding-001:embedContent"
    )
    assert seen["api_key"] == "test-key"
    assert seen["payload"] == {
        "content": {"parts": [{"text": "hello from slack"}]},
        "taskType": "RETRIEVAL_DOCUMENT",
        "outputDimensionality": 3,
    }


async def test_gemini_provider_raises_safe_error_on_api_failure() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "bad key"}})

    provider = GeminiEmbeddingProvider(
        api_key="secret-key",
        dimensions=3,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(GeminiEmbeddingError, match="status=403") as error:
        await provider.embed("sha256:input", "hello")

    assert "secret-key" not in str(error.value)
    assert "bad key" not in str(error.value)
