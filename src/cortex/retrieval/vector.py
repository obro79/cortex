from __future__ import annotations

from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.indexing.vector_memory import InMemoryVectorIndex
from cortex.ingestion.payloads import sha256_digest

from .candidates import Candidate
from .query import QueryPlan


class VectorRetriever:
    def __init__(
        self,
        *,
        vector_index: InMemoryVectorIndex,
        source_chunks: InMemorySourceChunkRepository,
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
        results = await self.vector_index.search(
            self.collection, embedding.vector, limit
        )
        candidates = []
        for result in results:
            payload = result.get("payload", {})
            if payload.get("workspace_id") != workspace_id:
                continue
            chunk_id = payload.get("source_chunk_id")
            if isinstance(chunk_id, str):
                candidates.append(
                    Candidate(
                        source_chunk=self.source_chunks.get_by_id(chunk_id),
                        vector_score=1.0,
                        paths={"vector"},
                    )
                )
        return candidates
