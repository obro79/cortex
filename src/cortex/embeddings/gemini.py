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
    model: str = "gemini-embedding-2"
    dimensions: int = 1536
    version: str = "gemini2-1536-v1"
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
            "content": {"parts": [{"text": self._task_instruction(input_text)}]},
            "outputDimensionality": self.dimensions,
        }
        try:
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
        except httpx.RequestError as error:
            raise GeminiEmbeddingError(
                "Gemini embedding request failed: transport_error"
            ) from error
        if response.status_code >= 400:
            raise GeminiEmbeddingError(
                f"Gemini embedding request failed: status={response.status_code}"
            )

        try:
            body = response.json()
            values = (
                body.get("embedding", {}).get("values")
                if isinstance(body, dict)
                else None
            )
        except ValueError as error:
            raise GeminiEmbeddingError(
                "Gemini embedding response was not valid JSON"
            ) from error
        if not isinstance(values, list) or not values:
            raise GeminiEmbeddingError(
                "Gemini embedding response did not include values"
            )
        try:
            vector = [float(value) for value in values]
        except (TypeError, ValueError) as error:
            raise GeminiEmbeddingError(
                "Gemini embedding response included invalid values"
            ) from error
        if len(vector) != self.dimensions:
            actual = len(vector)
            raise GeminiEmbeddingError(
                "Gemini embedding dimensions mismatch: "
                f"expected={self.dimensions} actual={actual}"
            )

        vector_bytes = ",".join(str(value) for value in vector).encode()
        return EmbeddingOutput(vector=vector, vector_hash=sha256_digest(vector_bytes))

    def _task_instruction(self, input_text: str) -> str:
        """Apply the asymmetric retrieval prefixes required by Embedding 2."""
        if self.task_type == "RETRIEVAL_QUERY":
            return f"task: search result | query: {input_text}"
        if self.task_type == "RETRIEVAL_DOCUMENT":
            return f"title: none | text: {input_text}"
        raise GeminiEmbeddingError("unsupported Gemini embedding task type")
