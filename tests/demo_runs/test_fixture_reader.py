from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from cortex.demo_runs import FixtureDemoRunReportReader, LiveRunCounts
from cortex.demo_runs.contracts import DemoRunReport

_HASH_A = "sha256:" + "a" * 64
_HASH_B = "sha256:" + "b" * 64


def _report_payload() -> dict[str, object]:
    return {
        "mode": "controlled_live_run",
        "outcome": "passed",
        "live_data": True,
        "run_id_hash": _HASH_A,
        "environment": "local",
        "provider": "slack",
        "source_ref_hash": _HASH_B,
        "collection": "cortex-local-embedding",
        "counts": LiveRunCounts(
            raw_events=1,
            source_objects=1,
            source_chunks=1,
            embeddings_completed=1,
            vector_points_verified=1,
            query_requests=1,
            evidence_packs=1,
            failures=0,
        ),
        "stages": {"slack_backfill": "completed"},
        "disclosure": "Counts and opaque hashes only.",
    }


async def test_fixture_reader_refuses_to_fabricate_a_live_run_report() -> None:
    reader = FixtureDemoRunReportReader()

    assert (
        await reader.latest_report(workspace_id="ws_demo", trace_id="trace_demo")
        is None
    )


async def test_fixture_reader_returns_redacted_source_health() -> None:
    sources = await FixtureDemoRunReportReader().source_health(
        workspace_id="ws_demo", trace_id="trace_demo"
    )

    assert {source.mode for source in sources} == {"fixture"}
    assert all(source.source_ref_hash.startswith("sha256:") for source in sources)
    assert sum(source.counts.raw_events for source in sources) == 10
    assert all(source.counts.vector_points_verified == 0 for source in sources)
    serialized = json.dumps([source.model_dump(mode="json") for source in sources])
    assert "https://" not in serialized
    assert "fixture://" not in serialized
    assert "Postgres is the approved" not in serialized
    assert "token" not in serialized


def test_live_report_serialization_has_exact_persisted_schema() -> None:
    report = DemoRunReport(**_report_payload())

    assert set(report.model_dump()) == {
        "schema_version",
        "mode",
        "outcome",
        "live_data",
        "run_id_hash",
        "environment",
        "provider",
        "source_ref_hash",
        "collection",
        "counts",
        "freshness_seconds",
        "stages",
        "disclosure",
        "next_action",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_id_hash", "sha256:deadbeef"),
        ("source_ref_hash", "sha256:" + "not-hex" * 10),
    ],
)
def test_live_report_rejects_non_sha256_hashes(field: str, value: str) -> None:
    payload = _report_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        DemoRunReport(**payload)


@pytest.mark.parametrize(
    "stages",
    [
        {"SlackBackfill": "completed"},
        {"slack_backfill": "COMPLETED"},
        {"slack_backfill": "completed\nleaked"},
    ],
)
def test_live_report_rejects_unsafe_stage_codes(stages: dict[str, str]) -> None:
    payload = _report_payload()
    payload["stages"] = stages

    with pytest.raises(ValidationError):
        DemoRunReport(**payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("disclosure", "Read https://example.test for details"),
        ("disclosure", "line one\nline two"),
        ("next_action", "Visit www.example.test"),
        ("disclosure", "Slack message body: launch Thursday"),
        ("disclosure", "xoxb-not-a-safe-disclosure"),
        ("next_action", "github_pat_not-a-safe-next-action"),
    ],
)
def test_live_report_rejects_url_like_or_multiline_display_text(
    field: str, value: str
) -> None:
    payload = _report_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        DemoRunReport(**payload)
