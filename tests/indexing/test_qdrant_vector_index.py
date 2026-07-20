from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from cortex.config import Settings
from cortex.indexing.qdrant import QdrantVectorIndex, qdrant_point_id
from cortex.interfaces.vector_index import FilteredVectorIndex


class FakeQdrantClient:
    def __init__(self) -> None:
        self.collections: dict[str, int] = {}
        self.points: dict[str, dict[str, Any]] = {}
        self.upsert_calls: list[dict[str, Any]] = []
        self.search_calls: list[dict[str, Any]] = []
        self.deleted_ids: list[str] = []
        self.healthy = True
        self.distance = "Cosine"

    async def collection_exists(self, *, collection_name: str) -> bool:
        return collection_name in self.collections

    async def create_collection(
        self, *, collection_name: str, vectors_config: Any
    ) -> None:
        self.collections[collection_name] = vectors_config.size
        self.points[collection_name] = {}

    async def get_collection(self, *, collection_name: str) -> Any:
        return SimpleNamespace(
            config=SimpleNamespace(
                params=SimpleNamespace(
                    vectors=SimpleNamespace(
                        size=self.collections[collection_name], distance=self.distance
                    )
                )
            )
        )

    async def upsert(self, **kwargs: Any) -> None:
        self.upsert_calls.append(kwargs)
        for point in kwargs["points"]:
            self.points[kwargs["collection_name"]][str(point.id)] = point

    async def delete(self, **kwargs: Any) -> None:
        for point_id in kwargs["points_selector"].points:
            self.deleted_ids.append(str(point_id))
            self.points[kwargs["collection_name"]].pop(str(point_id), None)

    async def query_points(self, **kwargs: Any) -> Any:
        self.search_calls.append(kwargs)
        points = [
            SimpleNamespace(id=point.id, payload=point.payload, score=0.91)
            for point in self.points[kwargs["collection_name"]].values()
        ][: kwargs["limit"]]
        return SimpleNamespace(points=points)

    async def get_collections(self) -> Any:
        if not self.healthy:
            raise RuntimeError("unavailable")
        return SimpleNamespace()


async def test_qdrant_adapter_bootstraps_idempotently_and_uses_stable_point_ids() -> (
    None
):
    client = FakeQdrantClient()
    index = QdrantVectorIndex(client)
    filtered_index: FilteredVectorIndex = index

    await index.ensure_collection("cortex-test-gemini-v1-2", 2)
    await index.ensure_collection("cortex-test-gemini-v1-2", 2)
    await index.upsert(
        "cortex-test-gemini-v1-2",
        "embedding_chunk_1_v1",
        [0.1, 0.2],
        {"workspace_id": "ws_1", "status": "active", "provider": "slack"},
    )
    first_qdrant_id = client.upsert_calls[0]["points"][0].id
    await index.upsert(
        "cortex-test-gemini-v1-2",
        "embedding_chunk_1_v1",
        [0.3, 0.4],
        {"workspace_id": "ws_1", "status": "active", "provider": "slack"},
    )

    assert client.collections == {"cortex-test-gemini-v1-2": 2}
    assert client.upsert_calls[1]["points"][0].id == first_qdrant_id
    assert len(client.points["cortex-test-gemini-v1-2"]) == 1

    results = await filtered_index.search_filtered(
        "cortex-test-gemini-v1-2",
        [0.3, 0.4],
        filters={"workspace_id": "ws_1", "status": "active"},
        limit=10,
    )
    assert results == [
        {
            "id": "embedding_chunk_1_v1",
            "payload": {
                "workspace_id": "ws_1",
                "status": "active",
                "provider": "slack",
            },
            "score": 0.91,
        }
    ]
    assert client.search_calls[0]["query_filter"] is not None
    assert client.search_calls[0]["query"] == [0.3, 0.4]

    await index.delete("cortex-test-gemini-v1-2", "embedding_chunk_1_v1")
    assert client.deleted_ids == [str(first_qdrant_id)]
    assert await index.search("cortex-test-gemini-v1-2", [0.3, 0.4], 10) == []


async def test_qdrant_adapter_rejects_content_bearing_payloads_and_dimension_drift() -> (
    None
):
    client = FakeQdrantClient()
    index = QdrantVectorIndex(client)
    await index.ensure_collection("cortex-test-gemini-v1-2", 2)

    with pytest.raises(ValueError, match="content-bearing"):
        await index.upsert(
            "cortex-test-gemini-v1-2",
            "point_1",
            [0.1, 0.2],
            {"source_text": "protected source material"},
        )
    with pytest.raises(ValueError, match="not permitted"):
        await index.upsert(
            "cortex-test-gemini-v1-2",
            "point_1",
            [0.1, 0.2],
            {"title": "unbounded source content must not enter Qdrant"},
        )
    with pytest.raises(ValueError, match="too large"):
        await index.upsert(
            "cortex-test-gemini-v1-2",
            "point_1",
            [0.1, 0.2],
            {"workspace_id": "x" * 513},
        )
    with pytest.raises(ValueError, match="compact identifier"):
        await index.upsert(
            "cortex-test-gemini-v1-2",
            "private source text must not become a stored point identifier",
            [0.1, 0.2],
            {"workspace_id": "ws_1"},
        )
    with pytest.raises(ValueError, match="dimensions"):
        await index.ensure_collection("cortex-test-gemini-v1-2", 3)
    client.distance = "Dot"
    with pytest.raises(ValueError, match="distance"):
        await index.ensure_collection("cortex-test-gemini-v1-2", 2)


async def test_qdrant_health_reports_client_failures_without_raising() -> None:
    client = FakeQdrantClient()
    index = QdrantVectorIndex(client)

    assert await index.health() is True
    client.healthy = False
    assert await index.health() is False


async def test_qdrant_adapter_uses_query_points_and_match_any_with_real_client() -> (
    None
):
    """Exercise the Qdrant 1.18 client surface instead of a compatibility fake."""
    from qdrant_client import AsyncQdrantClient

    client = AsyncQdrantClient(location=":memory:")
    index = QdrantVectorIndex(client)
    collection = "cortex-real-client"
    await index.ensure_collection(collection, 2)
    await index.upsert(
        collection,
        "emb_chunk_1_v1",
        [0.1, 0.2],
        {
            "workspace_id": "ws_1",
            "source_chunk_id": "chunk_1",
            "provider": "slack",
            "source_allowlist_eligible": True,
        },
    )

    assert await index.search_filtered(
        collection,
        [0.1, 0.2],
        filters={"provider": ["linear", "slack"]},
        limit=1,
    ) == [
        {
            "id": "emb_chunk_1_v1",
            "payload": {
                "workspace_id": "ws_1",
                "source_chunk_id": "chunk_1",
                "provider": "slack",
                "source_allowlist_eligible": True,
            },
            "score": pytest.approx(1.0),
        }
    ]
    assert qdrant_point_id(collection, "emb_chunk_1_v1") != "emb_chunk_1_v1"
    await index.close()


def test_hosted_qdrant_settings_require_key_and_build_valid_collection_name() -> None:
    with pytest.raises(ValueError, match="QDRANT_API_KEY"):
        Settings(qdrant_url="https://example.cloud.qdrant.io")
    with pytest.raises(ValueError, match="collection name"):
        Settings(qdrant_collection_prefix="bad prefix")
    with pytest.raises(ValueError, match="require HTTPS"):
        Settings(
            qdrant_url="http://example.cloud.qdrant.io", qdrant_api_key="qdrant-secret"
        )

    settings = Settings(
        cortex_env="staging",
        qdrant_url="https://example.cloud.qdrant.io/",
        qdrant_api_key="qdrant-secret",
    )

    assert settings.qdrant_url == "https://example.cloud.qdrant.io"
    assert (
        settings.qdrant_collection_name(
            embedding_model="gemini-embedding-001",
            embedding_version="gemini-1536-v1",
            dimensions=1536,
        )
        == "cortex-staging-gemini-embedding-001-gemini-1536-v1-1536"
    )
