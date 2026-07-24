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
        model="gemini-embedding-2",
        dimensions=3,
        version="gemini-test-v1",
        transport=httpx.MockTransport(handler),
    )

    output = await provider.embed("sha256:input", "hello from slack")

    assert output.vector == [0.1, -0.2, 0.3]
    assert output.vector_hash.startswith("sha256:")
    assert seen["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-embedding-2:embedContent"
    )
    assert seen["api_key"] == "test-key"
    assert seen["payload"] == {
        "content": {"parts": [{"text": "title: none | text: hello from slack"}]},
        "outputDimensionality": 3,
    }


async def test_gemini_embedding_2_uses_query_instruction_without_task_type() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content.decode()))
        return httpx.Response(200, json={"embedding": {"values": [0.1, 0.2]}})

    provider = GeminiEmbeddingProvider(
        api_key="test-key",
        dimensions=2,
        task_type="RETRIEVAL_QUERY",
        transport=httpx.MockTransport(handler),
    )

    await provider.embed("sha256:query", "why are sessions invalidated?")

    assert "taskType" not in seen
    assert seen["content"] == {
        "parts": [
            {"text": ("task: search result | query: why are sessions invalidated?")}
        ]
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


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(200, text="not-json"), "not valid JSON"),
        (
            httpx.Response(200, json={"embedding": {"values": ["bad"]}}),
            "invalid values",
        ),
    ],
)
async def test_gemini_provider_normalizes_malformed_responses(
    response: httpx.Response, message: str
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return response

    provider = GeminiEmbeddingProvider(
        api_key="secret-key",
        dimensions=1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(GeminiEmbeddingError, match=message) as error:
        await provider.embed("sha256:input", "hello")

    assert "secret-key" not in str(error.value)


async def test_gemini_provider_normalizes_transport_errors() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network detail", request=request)

    provider = GeminiEmbeddingProvider(
        api_key="secret-key",
        dimensions=1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(GeminiEmbeddingError, match="transport_error") as error:
        await provider.embed("sha256:input", "hello")

    assert "secret-key" not in str(error.value)
