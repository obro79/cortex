from __future__ import annotations

from datetime import UTC, datetime

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.entities import SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.ingestion.payloads import sha256_digest


def source_object(
    object_type: str, content_text: str, metadata: dict[str, object]
) -> SourceObject:
    now = datetime.now(UTC)
    return SourceObject(
        id=f"so_{object_type}",
        workspace_id="ws_1",
        source_connection_id="src_1",
        provider=str(metadata["provider"]),
        object_type=object_type,
        external_object_id=f"external_{object_type}",
        external_object_key=f"{metadata['provider']}:{object_type}",
        title="Private title should not be needed",
        content_text=content_text,
        content_hash=sha256_digest(content_text.encode()),
        metadata_json={
            key: value for key, value in metadata.items() if key != "provider"
        },
        status=SourceObjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_phase9_chunks_use_content_free_labels_and_safe_metadata() -> None:
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(
        source_object(
            "linear_issue",
            "COR-123 contains private issue text.",
            {
                "provider": "linear",
                "source_kind": "linear_issue",
                "identifier": "COR-123",
            },
        )
    )[0]

    assert chunk.citation_label == "Linear issue"
    assert chunk.text == "COR-123 contains private issue text."
    assert "private issue text" not in str(chunk.metadata_json)
    assert chunk.metadata_json["identifier"] == "COR-123"


def test_repo_doc_chunk_marks_stale_without_copying_doc_text_to_metadata() -> None:
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(
        source_object(
            "repo_doc",
            "Redis is stale guidance.",
            {
                "provider": "repo_docs",
                "source_kind": "repo_doc",
                "path": "docs/session.md",
                "is_stale": True,
            },
        )
    )[0]

    assert chunk.citation_label == "Repo doc"
    assert chunk.metadata_json["is_stale"] is True
    assert "Redis is stale guidance" not in str(chunk.metadata_json)
