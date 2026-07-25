from __future__ import annotations

import pytest

from cortex.connectors.jira import (
    JiraImportPlan,
    JiraIssueSnapshot,
    JiraSnapshotPage,
    JiraSnapshotPageInput,
)
from cortex.ingestion.raw_events import RawEventInput


def test_jira_snapshot_normalizes_payload_and_carries_page_cursor() -> None:
    page_input = JiraSnapshotPageInput(project_ids=("CORE",), page_size=50)
    issue = JiraIssueSnapshot.from_provider_payload(
        {
            "id": "1001",
            "key": "CORE-12",
            "self": "https://jira.example/rest/api/3/issue/1001",
            "fields": {
                "summary": "Snapshot foundation",
                "description": "Supplied offline.",
                "updated": "2026-07-19T12:00:00Z",
                "project": {"id": "2001"},
                "status": {"name": "In Progress"},
            },
        }
    )
    page = JiraSnapshotPage(page_input, (issue,), next_cursor="cursor-2")

    assert issue.to_payload()["project_id"] == "2001"
    assert page.next_page_input == JiraSnapshotPageInput(
        project_ids=("CORE",), cursor="cursor-2", page_size=50
    )


async def test_jira_import_plan_submits_events_to_supplied_seam() -> None:
    class RecordingIngestion:
        def __init__(self) -> None:
            self.items: list[RawEventInput] = []

        async def ingest(self, item: RawEventInput) -> str:
            self.items.append(item)
            return "accepted"

    issue = JiraIssueSnapshot.from_provider_payload(
        {"id": "1001", "key": "CORE-12", "fields": {"summary": "Plan"}}
    )
    plan = JiraImportPlan(
        workspace_id="ws_1",
        source_connection_id="src_jira",
        snapshot=JiraSnapshotPage(JiraSnapshotPageInput(), (issue,)),
    )
    ingestion = RecordingIngestion()

    execution = await plan.execute(ingestion)

    assert execution.submitted == 1
    assert execution.results == ("accepted",)
    assert ingestion.items[0].provider == "jira"
    assert ingestion.items[0].payload == {
        "connector_mode": "planned_snapshot",
        "issue": issue.to_payload(),
    }


def test_jira_snapshot_input_rejects_unsafe_pagination_values() -> None:
    with pytest.raises(ValueError, match="between"):
        JiraSnapshotPageInput(page_size=101)
    with pytest.raises(ValueError, match="non-empty"):
        JiraSnapshotPageInput(cursor=" ")
