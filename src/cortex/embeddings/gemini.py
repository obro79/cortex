from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from cortex.embeddings.deterministic import EmbeddingOutput
from cortex.ingestion.payloads import sha256_digest


class GeminiEmbeddingError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeminiEmbeddingProvider:
    api_key: str
    model: str = "gemini-embedding-001"
    dimensions: int = 1536
    version: str = "gemini-1536-v1"
    task_type: str = "RETRIEVAL_DOCUMENT"
    endpoint_base: str = "https://generativelanguage.googleapis.com/v1beta"
    timeout_seconds: float = 15.0
    transport: httpx.AsyncBaseTransport | None = None

    provider_name: str = "gemini"

    async def embed(self, input_text_hash: str, input_text: str) -> EmbeddingOutput:
        if not self.api_key:
            raise GeminiEmbeddingError("GEMINI_API_KEY is required")
        if not input_text:
            raise GeminiEmbeddingError("input text is required for Gemini embeddings")

        url = f"{self.endpoint_base}/models/{self.model}:embedContent"
        payload: dict[str, Any] = {
            "content": {"parts": [{"text": input_text}]},
            "taskType": self.task_type,
            "outputDimensionality": self.dimensions,
        }
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds, transport=self.transport
        ) as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
                json=payload,
            )
        if response.status_code >= 400:
            raise GeminiEmbeddingError(
                f"Gemini embedding request failed: status={response.status_code}"
            )

        values = response.json().get("embedding", {}).get("values")
        if not isinstance(values, list) or not values:
            raise GeminiEmbeddingError(
                "Gemini embedding response did not include values"
            )
        vector = [float(value) for value in values]
        if len(vector) != self.dimensions:
            actual = len(vector)
            raise GeminiEmbeddingError(
                "Gemini embedding dimensions mismatch: "
                f"expected={self.dimensions} actual={actual}"
            )

        vector_bytes = ",".join(str(value) for value in vector).encode()
        return EmbeddingOutput(vector=vector, vector_hash=sha256_digest(vector_bytes))
