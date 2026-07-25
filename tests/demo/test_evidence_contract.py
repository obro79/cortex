from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cortex.demo.evidence_contract import (
    EvidenceCitation,
    EvidenceContractEvaluator,
)


@dataclass(frozen=True)
class Record:
    fixture_id: str
    provider: str
    decisive: bool
    source_updated_at: datetime
    is_stale: bool = False
    evidence_class: str = ""


@dataclass(frozen=True)
class Manifest:
    task_ref: str
    records: tuple[Record, ...]


def _manifest() -> Manifest:
    now = datetime(2026, 7, 24, 12, tzinfo=UTC)
    decisive = (
        Record("slack-live", "slack", True, now),
        Record("github-pr", "github", True, now - timedelta(minutes=2)),
        Record("jira-cor-123", "jira", True, now - timedelta(minutes=3)),
        Record("email-impact", "email", True, now - timedelta(minutes=4)),
        Record("drive-stale", "google_drive", True, now - timedelta(days=20), True),
        Record("checkpoint", "agent_session", True, now - timedelta(minutes=5)),
    )
    near_misses = tuple(
        Record(f"near-miss-{index}", "github", False, now, evidence_class="near_miss")
        for index in range(30)
    )
    background = tuple(
        Record(f"background-{index}", "jira", False, now) for index in range(153)
    )
    return Manifest("COR-123", decisive + near_misses + background)


def _citations() -> tuple[EvidenceCitation, ...]:
    manifest = _manifest()
    by_id = {record.fixture_id: record for record in manifest.records}
    return tuple(
        EvidenceCitation(
            fixture_id=fixture_id,
            provider=by_id[fixture_id].provider,
            task_ref="COR-123",
            source_updated_at=by_id[fixture_id].source_updated_at,
            mode="live" if fixture_id == "slack-live" else "imported_snapshot",
            freshness="stale" if fixture_id == "drive-stale" else "fresh",
            relationship_state=(
                "conflicting" if fixture_id == "drive-stale" else "supporting"
            ),
            metadata={"synthetic_demo": True},
        )
        for fixture_id in (
            "slack-live",
            "github-pr",
            "jira-cor-123",
            "email-impact",
            "drive-stale",
            "checkpoint",
        )
    )


def test_evidence_contract_reports_a_complete_safe_post_live_corpus() -> None:
    report = EvidenceContractEvaluator().evaluate(_manifest(), _citations())

    assert report.passed is True
    assert report.corpus_record_count == 189
    assert report.near_miss_count == 30
    assert report.observed_citation_fixture_ids[0] == "slack-live"
    assert report.as_dict()["failures"] == []


def test_evidence_contract_records_exact_failures_for_bad_scope_conflict_and_data() -> (
    None
):
    citations = list(_citations())
    citations[0] = EvidenceCitation(
        **{**citations[0].__dict__, "task_ref": "PAY-88", "metadata": {"token": "nope"}}
    )
    citations[4] = EvidenceCitation(
        **{
            **citations[4].__dict__,
            "freshness": "fresh",
            "relationship_state": "supporting",
        }
    )
    report = EvidenceContractEvaluator().evaluate(_manifest(), citations)

    failures = {failure.code: failure for failure in report.failures}
    assert report.passed is False
    assert failures["citation_task_scope"].observed == ("slack-live",)
    assert failures["stale_drive_conflict"].observed == {
        "freshness": "fresh",
        "relationship_state": "supporting",
    }
    assert failures["forbidden_data_exposed"].observed == ("slack-live.token",)


def test_evidence_contract_rejects_near_miss_and_non_prioritized_slack() -> None:
    citations = list(_citations())
    citations = citations[1:] + [citations[0]]
    citations.append(
        EvidenceCitation(
            fixture_id="near-miss-0",
            provider="github",
            task_ref="COR-123",
            source_updated_at=datetime(2026, 7, 24, tzinfo=UTC),
            mode="imported_snapshot",
            freshness="fresh",
        )
    )

    report = EvidenceContractEvaluator().evaluate(_manifest(), citations)

    assert {failure.code for failure in report.failures} >= {
        "near_miss_cited",
        "fresh_slack_priority",
    }
