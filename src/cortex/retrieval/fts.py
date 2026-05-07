from __future__ import annotations

from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.contracts.enums import SourceChunkStatus

from .candidates import Candidate
from .query import QueryPlan


class FtsRetriever:
    def __init__(self, source_chunks: InMemorySourceChunkRepository) -> None:
        self.source_chunks = source_chunks

    def retrieve(
        self,
        *,
        workspace_id: str,
        plan: QueryPlan,
        chunking_version: str,
        limit: int,
    ) -> list[Candidate]:
        chunks = self.source_chunks.search_fts(
            workspace_id=workspace_id,
            query=plan.normalized_query,
            status=SourceChunkStatus.ACTIVE,
            chunking_version=chunking_version,
        )
        return [
            Candidate(source_chunk=chunk, lexical_score=1.0, paths={"fts"})
            for chunk in chunks[:limit]
        ]
