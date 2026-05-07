import pytest

from cortex.indexing.vector_memory import InMemoryVectorIndex


async def test_in_memory_vector_index_upsert_search_delete_and_health() -> None:
    index = InMemoryVectorIndex()
    await index.ensure_collection("fixture", 2)
    await index.upsert(
        "fixture",
        "point_1",
        [0.1, 0.2],
        {
            "workspace_id": "ws_1",
            "source_chunk_id": "chunk_1",
            "status": "active",
            "chunking_version": "chunking-v1",
        },
    )

    assert await index.health() is True
    assert (await index.search("fixture", [0.1, 0.2], 10))[0]["id"] == "point_1"
    await index.delete("fixture", "point_1")
    assert await index.search("fixture", [0.1, 0.2], 10) == []


async def test_vector_payload_rejects_content_fields() -> None:
    index = InMemoryVectorIndex()
    await index.ensure_collection("fixture", 2)

    with pytest.raises(ValueError):
        await index.upsert("fixture", "point_1", [0.1, 0.2], {"chunk_text": "secret"})
