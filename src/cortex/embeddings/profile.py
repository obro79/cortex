"""One compatible embedding/index identity for a Cortex runtime.

The profile is deliberately created at the composition boundary.  It ensures a
document embedding, query embedding, persisted embedding record, and Qdrant
collection all share the same provider/model/version/dimension contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from cortex.chunking.config import (
    EmbeddingsConfig,
    RetrievalConfig,
    load_retrieval_config,
)
from cortex.config import Settings

from .deterministic import DeterministicEmbeddingProvider, EmbeddingProvider
from .gemini import GeminiEmbeddingProvider


@dataclass(frozen=True)
class EmbeddingIndexProfile:
    """Embedding and collection identity shared by indexing and retrieval."""

    provider: str
    model: str
    version: str
    dimensions: int
    collection: str
    mode: str
    # The profile is useful in diagnostics and tests; its representation must
    # never turn a configured provider credential into log output.
    _api_key: str = field(default="", repr=False)

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        config: RetrievalConfig | None = None,
    ) -> EmbeddingIndexProfile:
        embeddings = (config or load_retrieval_config()).embeddings
        provider, model, dimensions = _profile_identity(
            settings=settings,
            embeddings=embeddings,
        )
        return cls(
            provider=provider,
            model=model,
            version=embeddings.version,
            dimensions=dimensions,
            collection=settings.qdrant_collection_name(
                embedding_model=model,
                embedding_version=embeddings.version,
                dimensions=dimensions,
            ),
            mode=settings.cortex_embedding_mode,
            _api_key=settings.gemini_api_key,
        )

    @property
    def document_task_type(self) -> str:
        return "retrieval_document"

    def document_embedder(self) -> EmbeddingProvider:
        return self._embedder(task_type="RETRIEVAL_DOCUMENT")

    def query_embedder(self) -> EmbeddingProvider:
        return self._embedder(task_type="RETRIEVAL_QUERY")

    def _embedder(self, *, task_type: str) -> EmbeddingProvider:
        if self.mode == "real":
            return cast(
                EmbeddingProvider,
                GeminiEmbeddingProvider(
                    api_key=self._api_key,
                    model=self.model,
                    dimensions=self.dimensions,
                    version=self.version,
                    task_type=task_type,
                ),
            )
        return DeterministicEmbeddingProvider(
            dimensions=self.dimensions,
            version=self.version,
        )


def _profile_identity(
    *, settings: Settings, embeddings: EmbeddingsConfig
) -> tuple[str, str, int]:
    if settings.cortex_embedding_mode == "real":
        return (
            embeddings.prod_provider,
            embeddings.prod_model,
            embeddings.prod_dimensions,
        )
    # Deterministic embeddings are an explicit local/test mode.  They retain a
    # stable provider model but still use the same collection naming rule as
    # real deployments rather than a hidden fixture collection.
    return embeddings.dev_provider, "fixture-vector-v1", 16
