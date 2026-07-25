from __future__ import annotations

import pytest

from cortex.connectors.google_drive import (
    GoogleDriveFileSnapshot,
    GoogleDriveImportPlan,
    GoogleDriveSnapshotPage,
    GoogleDriveSnapshotPageInput,
)
from cortex.ingestion.raw_events import RawEventInput


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


def test_google_drive_snapshot_input_rejects_unsafe_pagination_values() -> None:
    with pytest.raises(ValueError, match="between"):
        GoogleDriveSnapshotPageInput(page_size=1001)
    with pytest.raises(ValueError, match="non-empty"):
        GoogleDriveSnapshotPageInput(folder_id=" ")
