from datetime import UTC, datetime

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.entities import SourceFile, SourceObject
from cortex.contracts.enums import SourceObjectStatus


def source_object(content_hash: str = "sha256:content") -> SourceObject:
    now = datetime.now(UTC)
    return SourceObject(
        id="so_1",
        workspace_id="ws_1",
        source_connection_id="src_1",
        provider="linear",
        object_type="linear_issue",
        external_object_id="COR-123",
        external_object_key="linear:COR-123",
        title="COR-123 migrate session reads",
        canonical_url="https://fixtures.local/linear/COR-123",
        content_hash=content_hash,
        metadata_json={"source_kind": "linear_task"},
        status=SourceObjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def source_file() -> SourceFile:
    now = datetime.now(UTC)
    return SourceFile(
        id="file_1",
        workspace_id="ws_1",
        source_object_id="so_1",
        source_connection_id="src_1",
        provider="slack",
        external_file_id="file_1",
        external_object_key="slack:file_1",
        content_type="image/png",
        content_hash="sha256:file",
        ocr_text="OCR: browser writes session token.",
        ocr_text_hash="sha256:ocr",
        metadata_json={},
        status=SourceObjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def slack_source_object() -> SourceObject:
    now = datetime.now(UTC)
    return SourceObject(
        id="so_slack_1",
        workspace_id="ws_1",
        source_connection_id="src_slack_1",
        provider="slack",
        object_type="slack_thread",
        external_object_id="T123:C123:1700000000.000100:1700000000.000100",
        external_object_key="slack:T123:C123:1700000000.000100:1700000000.000100",
        title="Slack thread",
        content_hash="sha256:slack-message",
        content_text="Project comet launch decision",
        metadata_json={
            "source_kind": "slack_message",
            "channel_id_hash": "sha256:channel",
            "message_ts": "1700000000.000100",
            "thread_ts": "1700000000.000100",
            "has_files": True,
            "has_links": True,
        },
        status=SourceObjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_source_object_chunk_has_stable_citation_and_hash() -> None:
    chunker = SourceAwareChunker(load_retrieval_config().chunking)

    first = chunker.chunks_for_source_object(source_object())[0]
    second = chunker.chunks_for_source_object(source_object())[0]

    assert first.id == second.id
    assert first.chunk_type == "linear_issue_overview"
    assert first.chunking_version == "chunking-v1"
    assert first.citation_url == "https://fixtures.local/linear/COR-123"
    assert "COR-123" in first.text
    assert first.metadata_json["provider"] == "linear"
    assert first.metadata_json["source_type"] == "linear_issue"


def test_source_file_chunker_creates_metadata_and_ocr_chunks() -> None:
    chunks = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_file(source_object(), source_file())

    assert [chunk.chunk_type for chunk in chunks] == ["file_metadata", "ocr_text"]
    assert chunks[1].text_hash is not None
    assert chunks[1].created_from_hash == "sha256:ocr"


def test_slack_source_object_chunk_uses_message_text_without_metadata_leak() -> None:
    chunker = SourceAwareChunker(load_retrieval_config().chunking)

    first = chunker.chunks_for_source_object(slack_source_object())[0]
    second = chunker.chunks_for_source_object(slack_source_object())[0]

    assert first.id == second.id
    assert first.chunk_type == "slack_message"
    assert first.text == "Project comet launch decision"
    assert first.citation_label == "Slack thread"
    assert "retrieval_text" not in first.metadata_json
    assert "Project comet" not in str(first.metadata_json)
    assert first.metadata_json["provider"] == "slack"
    assert first.metadata_json["source_type"] == "slack_thread"
