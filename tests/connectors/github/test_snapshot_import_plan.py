from __future__ import annotations

import pytest

from cortex.connectors.github import (
    GitHubImportPlan,
    GitHubSnapshotEvent,
    GitHubSnapshotPage,
    GitHubSnapshotPageInput,
)
from cortex.ingestion.raw_events import RawEventInput


def test_github_snapshot_normalizes_event_and_carries_checkpoint() -> None:
    page_input = GitHubSnapshotPageInput(repository_ids=("44",), page_size=25)
    event = GitHubSnapshotEvent.from_provider_event(
        {
            "repository": {"id": 44, "full_name": "acme/cortex"},
            "pull_request": {
                "id": 1,
                "number": 12,
                "title": "Fixture PR",
                "updated_at": "2026-07-19T12:00:00Z",
            },
        }
    )
    page = GitHubSnapshotPage(page_input, (event,), next_cursor="page-2")

    assert event.to_payload()["repository_full_name"] == "acme/cortex"
    assert page.next_page_input == GitHubSnapshotPageInput(
        repository_ids=("44",), cursor="page-2", page_size=25
    )


async def test_github_import_plan_submits_typed_events_to_supplied_seam() -> None:
    class RecordingIngestion:
        def __init__(self) -> None:
            self.items: list[RawEventInput] = []

        async def ingest(self, item: RawEventInput) -> str:
            self.items.append(item)
            return "accepted"

    event = GitHubSnapshotEvent.from_provider_event(
        {
            "repository": {"id": "44", "full_name": "acme/cortex"},
            "commit": {
                "sha": "abc123",
                "message": "Fixture commit",
                "timestamp": "2026-07-19T12:00:00Z",
            },
        }
    )
    plan = GitHubImportPlan(
        workspace_id="ws_1",
        source_connection_id="src_github",
        snapshot=GitHubSnapshotPage(GitHubSnapshotPageInput(), (event,)),
    )
    ingestion = RecordingIngestion()

    execution = await plan.execute(ingestion)

    assert execution.submitted == 1
    assert execution.results == ("accepted",)
    assert execution.next_page_input is None
    assert ingestion.items[0].provider == "github"
    assert ingestion.items[0].event_type == "github.commit.snapshot"
    assert ingestion.items[0].payload == {
        "connector_mode": "planned_snapshot",
        "event": event.to_payload(),
    }


def test_github_snapshot_input_rejects_unsafe_pagination_values() -> None:
    with pytest.raises(ValueError, match="between"):
        GitHubSnapshotPageInput(page_size=101)
    with pytest.raises(ValueError, match="non-empty"):
        GitHubSnapshotPageInput(cursor=" ")


def test_github_snapshot_rejects_unidentifiable_provider_event() -> None:
    with pytest.raises(ValueError, match="stable identifier"):
        GitHubSnapshotEvent.from_provider_event(
            {"repository": {"id": "44"}, "pull_request": {"title": "Missing"}}
        )
