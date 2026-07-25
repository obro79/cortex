from datetime import UTC, datetime

from cortex.contracts.entities import SourceFile, SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.events.in_memory import InMemoryEventBus
from cortex.normalization.publishers import SourceFilePublisher, SourceObjectPublisher


def source_object() -> SourceObject:
    now = datetime.now(UTC)
    return SourceObject(
        id="so_1",
        workspace_id="ws_1",
        source_connection_id="src_1",
        provider="linear",
        object_type="linear_issue",
        external_object_id="COR-123",
        external_object_key="linear:COR-123",
        normalized_version="fixture-normalizer-v1",
        content_hash="sha256:content",
        metadata_json={},
        status=SourceObjectStatus.ACTIVE,
        trace_id="trace_1",
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
        file_name_hash="sha256:name",
        content_type="image/png",
        storage_ref="fixture://files/file_1",
        content_hash="sha256:file",
        ocr_text="OCR text",
        ocr_text_hash="sha256:ocr",
        metadata_json={},
        status=SourceObjectStatus.ACTIVE,
        trace_id="trace_1",
        created_at=now,
        updated_at=now,
    )


async def test_source_object_upserted_envelope_is_pointer_only() -> None:
    bus = InMemoryEventBus()
    envelope = await SourceObjectPublisher(bus).publish_upserted(
        source_object(),
        raw_event_id="raw_1",
        payload_hash="sha256:payload",
        operation="inserted",
        parent_event_id="evt_raw_1",
        file_count=1,
        relationship_count=2,
    )

    assert envelope.event_type == "source_object.upserted"
    assert envelope.subject.type == "source_object"
    assert envelope.causation.raw_event_id == "raw_1"
    assert envelope.causation.source_object_id == "so_1"
    assert envelope.versions.normalized_version == "fixture-normalizer-v1"
    assert envelope.hashes.content_hash == "sha256:content"
    assert envelope.trace.parent_event_id == "evt_raw_1"
    assert envelope.payload == {
        "object_type": "linear_issue",
        "operation": "inserted",
        "file_count": 1,
        "relationship_count": 2,
    }
    assert bus.list_events() == [envelope]


async def test_source_file_fetched_envelope_omits_ocr_text_and_filename() -> None:
    envelope = await SourceFilePublisher(InMemoryEventBus()).publish_fetched(
        source_file(),
        raw_event_id="raw_1",
        source_object_id="so_1",
        payload_hash="sha256:payload",
        operation="inserted",
    )

    assert envelope.event_type == "source_file.fetched"
    assert envelope.subject.type == "source_file"
    assert envelope.hashes.content_hash == "sha256:file"
    assert envelope.payload == {"content_type": "image/png", "operation": "inserted"}
    assert "ocr_text" not in envelope.payload
    assert "file_name" not in envelope.payload
