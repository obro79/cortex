from cortex.chunking.config import load_retrieval_config
from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.retrieval.query import QueryPlanner
from cortex.retrieval.vector import VectorRetriever


class _VectorIndex:
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
    retriever = VectorRetriever(
        vector_index=_VectorIndex(),  # type: ignore[arg-type]
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
