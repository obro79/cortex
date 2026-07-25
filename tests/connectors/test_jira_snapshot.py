from __future__ import annotations

import pytest

from cortex.connectors.jira import (
    JiraImportPlan,
    JiraIssueSnapshot,
    JiraSnapshotPage,
    JiraSnapshotPageInput,
)
from cortex.contracts.entities import RawEvent
from cortex.contracts.enums import RawEventStatus
from cortex.ingestion.payloads import canonical_json_bytes
from cortex.ingestion.raw_events import RawEventInput
from cortex.normalization.normalizers.jira import normalize_jira_payload
from cortex.normalization.normalizers.provider_payloads import (
    ProviderNormalizationError,
)


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


def test_jira_snapshot_page_rejects_cursor_loops_and_oversized_pages() -> None:
    input = JiraSnapshotPageInput(cursor="cursor_1", page_size=1)
    issue = JiraIssueSnapshot.from_provider_payload(
        {"id": "1001", "key": "CORE-12", "fields": {"summary": "Plan"}}
    )

    with pytest.raises(ValueError, match="advance"):
        JiraSnapshotPage(input, (issue,), next_cursor="cursor_1")
    with pytest.raises(ValueError, match="exceeds"):
        JiraSnapshotPage(input, (issue, issue))


def test_jira_normalizer_accepts_only_the_safe_snapshot_contract() -> None:
    result = normalize_jira_payload(
        _raw_event("jira.issue.snapshot"),
        canonical_json_bytes(
            {
                "connector_mode": "planned_snapshot",
                "issue": {
                    "id": "1001",
                    "key": "CORE-12",
                    "title": "Snapshot foundation",
                    "description": "Private implementation details.",
                    "project_id": "2001",
                    "status": "In Progress",
                    "unexpected_provider_field": {"not": "stored"},
                },
            }
        ),
    )

    source_object = result.source_objects[0]
    assert source_object.metadata_json == {
        "source_kind": "jira_issue",
        "issue_key": "CORE-12",
        "project_id": "2001",
        "status": "In Progress",
    }
    assert "Private implementation details." in (source_object.content_text or "")
    with pytest.raises(ProviderNormalizationError, match="unsupported"):
        normalize_jira_payload(_raw_event("jira.issue.updated"), b"{}")


def _raw_event(event_type: str) -> RawEvent:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    return RawEvent(
        id="raw_jira_1",
        workspace_id="ws_1",
        source_connection_id="src_jira",
        provider="jira",
        external_event_id="jira_issue_1001",
        event_type=event_type,
        external_object_key="jira:CORE-12",
        idempotency_key="jira:1",
        payload_ref="memory://payload",
        payload_hash="sha256:payload",
        received_at=now,
        status=RawEventStatus.PUBLISHED,
        trace_id="trace_1",
        created_at=now,
        updated_at=now,
    )
