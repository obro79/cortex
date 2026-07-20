from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cortex.db.models import DemoRunReportRecord
from cortex.demo_runs import (
    DemoRunReport,
    DemoRunReportProjectionError,
    LiveRunCounts,
    SqlAlchemyDemoRunReportRepository,
    SqlAlchemyDemoRunReportStore,
    stable_demo_run_report_id,
)

_HASH_A = "sha256:" + "a" * 64
_HASH_B = "sha256:" + "b" * 64
_HASH_C = "sha256:" + "c" * 64


class _Result:
    def __init__(self, records: list[DemoRunReportRecord]) -> None:
        self.records = records

    def scalar_one_or_none(self) -> DemoRunReportRecord | None:
        assert len(self.records) <= 1
        return self.records[0] if self.records else None


class _ReportSession:
    """Small persistent async-session double for report projection contracts."""

    def __init__(self) -> None:
        self.records: dict[str, DemoRunReportRecord] = {}
        self.commits = 0

    async def get(
        self, _model: type[DemoRunReportRecord], record_id: str
    ) -> DemoRunReportRecord | None:
        return self.records.get(record_id)

    def add(self, record: DemoRunReportRecord) -> None:
        self.records[record.id] = record

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    @asynccontextmanager
    async def begin_nested(self) -> AsyncIterator[None]:
        yield

    async def execute(self, statement: Any) -> _Result:
        entity = statement.column_descriptions[0]["entity"]
        assert entity is DemoRunReportRecord
        params = statement.compile().params
        workspace_id = next(
            value for key, value in params.items() if key.startswith("workspace_id")
        )
        run_id_hash = next(
            (value for key, value in params.items() if key.startswith("run_id_hash")),
            None,
        )
        records = [
            record
            for record in self.records.values()
            if record.workspace_id == workspace_id
            and (run_id_hash is None or record.run_id_hash == run_id_hash)
        ]
        records.sort(
            key=lambda record: (
                record.completed_at,
                record.created_at,
                record.id,
            ),
            reverse=True,
        )
        # ``latest_report`` asks for LIMIT 1; identity lookups do not.
        if any(key.startswith("param") for key in params):
            records = records[:1]
        return _Result(records)


class _ReportSessionFactory:
    def __init__(self, session: _ReportSession) -> None:
        self.session = session

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[_ReportSession]:
        yield self.session


def _report(
    *, run_id_hash: str = _HASH_A, source_ref_hash: str = _HASH_B
) -> DemoRunReport:
    return DemoRunReport(
        mode="controlled_live_run",
        outcome="passed",
        live_data=True,
        run_id_hash=run_id_hash,
        environment="local",
        provider="slack",
        source_ref_hash=source_ref_hash,
        collection="cortex-local-embedding",
        counts=LiveRunCounts(
            raw_events=3,
            source_objects=3,
            source_chunks=4,
            embeddings_completed=4,
            vector_points_verified=4,
            query_requests=1,
            evidence_packs=1,
            failures=0,
        ),
        stages={"slack_backfill": "completed", "task_context": "completed"},
        disclosure="Aggregate counts and opaque hashes only.",
    )


async def test_sql_report_projection_is_redacted_and_idempotent() -> None:
    session = _ReportSession()
    repository = SqlAlchemyDemoRunReportRepository(session)  # type: ignore[arg-type]
    report = _report()

    persisted = await repository.record_report(
        workspace_id="ws_1",
        source_connection_id="source_conn_1",
        report=report,
    )
    replayed = await repository.record_report(
        workspace_id="ws_1",
        source_connection_id="source_conn_1",
        report=report,
    )

    assert persisted == report
    assert replayed == report
    assert len(session.records) == 1
    record = session.records[stable_demo_run_report_id("ws_1", _HASH_A)]
    serialized = str(record.__dict__)
    assert record.report_json == report.model_dump(mode="json")
    assert "C_PRIVATE_123" not in serialized
    assert "Slack message body" not in serialized
    assert "https://slack.example" not in serialized
    assert "xoxb-secret" not in serialized
    assert "query text" not in serialized


async def test_sql_report_projection_refuses_conflicting_replay() -> None:
    session = _ReportSession()
    repository = SqlAlchemyDemoRunReportRepository(session)  # type: ignore[arg-type]
    report = _report()
    await repository.record_report(
        workspace_id="ws_1",
        source_connection_id="source_conn_1",
        report=report,
    )

    with pytest.raises(DemoRunReportProjectionError, match="immutable"):
        await repository.record_report(
            workspace_id="ws_1",
            source_connection_id="source_conn_1",
            report=report.model_copy(update={"outcome": "partial"}),
        )


async def test_sql_report_reader_is_workspace_scoped_and_fails_closed() -> None:
    session = _ReportSession()
    repository = SqlAlchemyDemoRunReportRepository(session)  # type: ignore[arg-type]
    now = datetime.now(UTC)
    await repository.record_report(
        workspace_id="ws_1",
        source_connection_id="source_conn_1",
        report=_report(),
        completed_at=now,
    )
    await repository.record_report(
        workspace_id="ws_2",
        source_connection_id="source_conn_2",
        report=_report(run_id_hash=_HASH_C, source_ref_hash=_HASH_C),
        completed_at=now + timedelta(seconds=1),
    )

    assert await repository.latest_report(workspace_id="ws_1") == _report()
    assert await repository.latest_report(workspace_id="ws_2") == _report(
        run_id_hash=_HASH_C, source_ref_hash=_HASH_C
    )

    corrupt_id = stable_demo_run_report_id("ws_1", _HASH_B)
    session.records[corrupt_id] = DemoRunReportRecord(
        id=corrupt_id,
        workspace_id="ws_1",
        source_connection_id="source_conn_1",
        provider="slack",
        run_id_hash=_HASH_B,
        source_ref_hash=_HASH_B,
        collection="cortex-local-embedding",
        outcome="passed",
        report_json={"untrusted": "Slack message body"},
        completed_at=now + timedelta(seconds=2),
        created_at=now + timedelta(seconds=2),
    )

    # The reader will not silently fall back to the older legitimate report.
    assert await repository.latest_report(workspace_id="ws_1") is None


async def test_store_owns_commit_without_exposing_a_public_write_route() -> None:
    session = _ReportSession()
    store = SqlAlchemyDemoRunReportStore(_ReportSessionFactory(session))  # type: ignore[arg-type]
    report = _report()

    await store.record_report(
        workspace_id="ws_1",
        source_connection_id="source_conn_1",
        report=report,
    )

    assert session.commits == 1
    assert (
        await store.latest_report(workspace_id="ws_1", trace_id="trace_secret")
        == report
    )
