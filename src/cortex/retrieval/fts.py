from __future__ import annotations

from cortex.contracts.enums import SourceChunkStatus
from cortex.utils.asyncio import maybe_await

from .candidates import Candidate
from .query import QueryPlan


class FtsRetriever:
    def __init__(self, source_chunks: object) -> None:
        self.source_chunks = source_chunks

    async def retrieve(
        self,
        *,
        workspace_id: str,
        plan: QueryPlan,
        chunking_version: str,
        limit: int,
    ) -> list[Candidate]:
        search = getattr(self.source_chunks, "search_fts_ranked", None)
        if search is None:
            raise TypeError("source chunk repository does not support ranked FTS")
        matches = await maybe_await(
            search(
                workspace_id=workspace_id,
                query=plan.normalized_query,
                status=SourceChunkStatus.ACTIVE,
                chunking_version=chunking_version,
                limit=limit,
            )
        )
        return [
            Candidate(
                source_chunk=chunk,
                lexical_score=score,
                paths={"fts"},
                score_provenance={"lexical": score},
            )
            for chunk, score in matches
        ]
