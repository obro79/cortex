from cortex.chunking.config import load_retrieval_config
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.entities import SourceObject


def test_source_chunk_repository_upsert_noop_update_and_fts_search(
    phase4_source_object: SourceObject,
) -> None:
    repository = InMemorySourceChunkRepository()
    chunker = SourceAwareChunker(load_retrieval_config().chunking)
    first_chunk = chunker.chunks_for_source_object(phase4_source_object)[0]
    changed_object = phase4_source_object.model_copy(
        update={"content_hash": "sha256:two"}
    )
    changed_chunk = chunker.chunks_for_source_object(changed_object)[0]

    inserted = repository.upsert_many([first_chunk])
    noop = repository.upsert_many([first_chunk])
    updated = repository.upsert_many([changed_chunk])
    matches = repository.search_fts(
        workspace_id="ws_1", query="session reads", chunking_version="chunking-v1"
    )

    assert inserted[0].operation == "inserted"
    assert noop[0].operation == "noop"
    assert updated[0].operation == "updated"
    assert matches[0].id == first_chunk.id
