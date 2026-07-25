from cortex.chunking.config import load_retrieval_config
from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.retrieval.query import QueryPlanner
from cortex.retrieval.vector import VectorRetriever


class _VectorIndex:
    def __init__(self) -> None:
        self.filters: dict[str, object] | None = None

    async def search_filtered(
        self,
        collection: str,
        vector: list[float],
        *,
        filters: dict[str, object],
        limit: int,
    ) -> list[dict[str, object]]:
        self.filters = filters
        return await self.search(collection, vector, limit)

    async def search(
        self, collection: str, vector: list[float], limit: int
    ) -> list[dict[str, object]]:
        del collection, vector, limit
        return [
            {
                "id": "point_disallowed",
                "payload": {
                    "workspace_id": "ws_1",
                    "source_chunk_id": "chunk_disallowed",
                    "source_object_id": "so_disallowed",
                    "provider": "slack",
                },
            }
        ]


class _NoHydrationRepository:
    def get_by_id(self, source_chunk_id: str) -> object:
        raise AssertionError(f"unexpected hydration for {source_chunk_id}")


async def test_vector_metadata_filters_run_before_canonical_chunk_hydration() -> None:
    config = load_retrieval_config()
    index = _VectorIndex()
    retriever = VectorRetriever(
        vector_index=index,  # type: ignore[arg-type]
        source_chunks=_NoHydrationRepository(),
        embedder=DeterministicEmbeddingProvider(
            dimensions=16, version=config.embeddings.version
        ),
    )

    candidates = await retriever.retrieve(
        workspace_id="ws_1",
        plan=QueryPlanner().plan(
            query="session reads",
            provider_filters=["github"],
            source_allowlist=["so_allowed"],
        ),
        limit=10,
    )

    assert candidates == []
    assert index.filters == {
        "workspace_id": "ws_1",
        "status": "active",
        "embedding_version": config.embeddings.version,
        "provider": ["github"],
        "source_object_id": ["so_allowed"],
    }
