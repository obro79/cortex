from __future__ import annotations

import pytest

from cortex.connectors.google_drive import (
    GoogleDriveFileSnapshot,
    GoogleDriveImportPlan,
    GoogleDriveSnapshotPage,
    GoogleDriveSnapshotPageInput,
)
from cortex.contracts.entities import RawEvent
from cortex.contracts.enums import RawEventStatus
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore, canonical_json_bytes
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository, RawEventInput
from cortex.ingestion.service import RawEventIngestionService
from cortex.normalization.normalizers.google_drive import normalize_google_drive_payload
from cortex.normalization.normalizers.provider_payloads import (
    ProviderNormalizationError,
)


def test_google_drive_snapshot_normalizes_payload_and_carries_page_cursor() -> None:
    page_input = GoogleDriveSnapshotPageInput(folder_id="folder_1", page_size=250)
    file = GoogleDriveFileSnapshot.from_provider_payload(
        {
            "id": "file_1",
            "name": "Architecture",
            "mimeType": "application/vnd.google-apps.document",
            "description": "A supplied snapshot.",
            "modifiedTime": "2026-07-19T12:00:00Z",
            "parents": ["folder_1", ""],
            "trashed": False,
        }
    )
    page = GoogleDriveSnapshotPage(page_input, (file,), next_cursor="token-2")

    assert file.to_payload()["parent_ids"] == ["folder_1"]
    assert page.next_page_input == GoogleDriveSnapshotPageInput(
        folder_id="folder_1", cursor="token-2", page_size=250
    )


async def test_google_drive_import_plan_submits_events_to_supplied_seam() -> None:
    class RecordingIngestion:
        def __init__(self) -> None:
            self.items: list[RawEventInput] = []

        async def ingest(self, item: RawEventInput) -> str:
            self.items.append(item)
            return "accepted"

    file = GoogleDriveFileSnapshot.from_provider_payload(
        {
            "id": "file_1",
            "name": "Architecture",
            "mimeType": "text/plain",
        }
    )
    plan = GoogleDriveImportPlan(
        workspace_id="ws_1",
        source_connection_id="src_drive",
        snapshot=GoogleDriveSnapshotPage(GoogleDriveSnapshotPageInput(), (file,)),
    )
    ingestion = RecordingIngestion()

    execution = await plan.execute(ingestion)

    assert execution.submitted == 1
    assert execution.results == ("accepted",)
    assert ingestion.items[0].provider == "google_drive"
    assert ingestion.items[0].payload == {
        "connector_mode": "planned_snapshot",
        "file": file.to_payload(),
    }


async def test_google_drive_import_plan_uses_common_raw_event_ingestion() -> None:
    file = GoogleDriveFileSnapshot.from_provider_payload(
        {"id": "file_1", "name": "Architecture", "mimeType": "text/plain"}
    )
    plan = GoogleDriveImportPlan(
        workspace_id="ws_1",
        source_connection_id="src_drive",
        snapshot=GoogleDriveSnapshotPage(GoogleDriveSnapshotPageInput(), (file,)),
    )
    repository = InMemoryRawEventRepository()
    event_bus = InMemoryEventBus()
    ingestion = RawEventIngestionService(
        repository,
        InMemoryPayloadStore(),
        RawEventPublisher(event_bus),
    )

    execution = await plan.execute(ingestion)

    raw_event = repository.get_by_id(execution.results[0].raw_event_id)
    assert raw_event.status == RawEventStatus.PUBLISHED
    assert event_bus.list_events()[0].event_type == "raw_event.persisted"
    assert event_bus.list_events()[0].payload == {
        "provider_event_type": "google_drive.file.snapshot"
    }


def test_google_drive_snapshot_input_rejects_unsafe_pagination_values() -> None:
    with pytest.raises(ValueError, match="between"):
        GoogleDriveSnapshotPageInput(page_size=1001)
    with pytest.raises(ValueError, match="non-empty"):
        GoogleDriveSnapshotPageInput(folder_id=" ")


def test_google_drive_snapshot_page_rejects_cursor_loops_and_oversized_pages() -> None:
    input = GoogleDriveSnapshotPageInput(cursor="cursor_1", page_size=1)
    file = GoogleDriveFileSnapshot.from_provider_payload(
        {"id": "file_1", "name": "Architecture", "mimeType": "text/plain"}
    )

    with pytest.raises(ValueError, match="advance"):
        GoogleDriveSnapshotPage(input, (file,), next_cursor="cursor_1")
    with pytest.raises(ValueError, match="exceeds"):
        GoogleDriveSnapshotPage(input, (file, file))


def test_google_drive_normalizer_accepts_only_the_safe_snapshot_contract() -> None:
    event = _raw_event("google_drive.file.snapshot")
    result = normalize_google_drive_payload(
        event,
        canonical_json_bytes(
            {
                "connector_mode": "planned_snapshot",
                "file": {
                    "id": "file_1",
                    "name": "Architecture",
                    "mime_type": "text/plain",
                    "description": "Private implementation details.",
                    "parent_ids": ["folder_1"],
                    "trashed": False,
                    "unexpected_provider_field": {"not": "stored"},
                },
            }
        ),
    )

    source_object = result.source_objects[0]
    assert source_object.metadata_json == {
        "source_kind": "drive_file",
        "mime_type": "text/plain",
        "parent_ids": ["folder_1"],
        "trashed": False,
    }
    assert "Private implementation details." in (source_object.content_text or "")
    with pytest.raises(ProviderNormalizationError, match="unsupported"):
        normalize_google_drive_payload(_raw_event("google_drive.file.changed"), b"{}")


def _raw_event(event_type: str) -> RawEvent:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    return RawEvent(
        id="raw_drive_1",
        workspace_id="ws_1",
        source_connection_id="src_drive",
        provider="google_drive",
        external_event_id="drive_file_1",
        event_type=event_type,
        external_object_key="google_drive:file:file_1",
        idempotency_key="google_drive:1",
        payload_ref="memory://payload",
        payload_hash="sha256:payload",
        received_at=now,
        status=RawEventStatus.PUBLISHED,
        trace_id="trace_1",
        created_at=now,
        updated_at=now,
    )
