from __future__ import annotations

from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.ingestion.payloads import sha256_digest
from cortex.interfaces.vector_index import VectorIndex
from cortex.utils.asyncio import maybe_await

from .candidates import Candidate
from .query import QueryPlan


class VectorRetriever:
    """Hydrate canonical chunks only after vector-result eligibility checks.

    Vector adapters should implement ``search_filtered`` and enforce the supplied
    workspace, active-status, embedding-version, provider, and source-object
    constraints server-side. The payload checks below remain a fail-closed
    defense for adapters that only implement the base ``VectorIndex`` protocol.
    """

    def __init__(
        self,
        *,
        vector_index: VectorIndex,
        source_chunks: object,
        embedder: DeterministicEmbeddingProvider,
        collection: str = "fixture-cortex-dev",
    ) -> None:
        self.vector_index = vector_index
        self.source_chunks = source_chunks
        self.embedder = embedder
        self.collection = collection

    async def retrieve(
        self,
        *,
        workspace_id: str,
        plan: QueryPlan,
        limit: int,
    ) -> list[Candidate]:
        query_hash = sha256_digest(plan.normalized_query.encode())
        embedding = self.embedder.embed(query_hash)
        allowed_providers = {provider.lower() for provider in plan.provider_filters}
        allowed_sources = set(plan.source_allowlist)
        filtered_search = getattr(self.vector_index, "search_filtered", None)
        if callable(filtered_search):
            filters: dict[str, object] = {
                "workspace_id": workspace_id,
                "status": "active",
                "embedding_version": self.embedder.version,
            }
            if allowed_providers:
                filters["provider"] = sorted(allowed_providers)
            if allowed_sources:
                filters["source_object_id"] = sorted(allowed_sources)
            results = await maybe_await(
                filtered_search(
                    self.collection,
                    embedding.vector,
                    filters=filters,
                    limit=limit,
                )
            )
        else:
            results = await self.vector_index.search(
                self.collection, embedding.vector, limit
            )
        candidates = []
        for result in results:
            payload = result.get("payload", {})
            if (
                not isinstance(payload, dict)
                or payload.get("workspace_id") != workspace_id
            ):
                continue
            chunk_id = payload.get("source_chunk_id")
            source_object_id = payload.get("source_object_id")
            provider = payload.get("provider")
            if not isinstance(chunk_id, str):
                continue
            if allowed_sources and source_object_id not in allowed_sources:
                continue
            if allowed_providers and (
                not isinstance(provider, str)
                or provider.lower() not in allowed_providers
            ):
                continue
            get_by_id = getattr(self.source_chunks, "get_by_id", None)
            if get_by_id is None:
                raise TypeError(
                    "source chunk repository does not support chunk hydration"
                )
            chunk = await maybe_await(get_by_id(chunk_id))
            raw_score = result.get("score", 1.0)
            score = float(raw_score) if isinstance(raw_score, int | float) else 1.0
            candidates.append(
                Candidate(
                    source_chunk=chunk,
                    vector_score=score,
                    paths={"vector"},
                    score_provenance={"vector": score},
                )
            )
        return candidates
