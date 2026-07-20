"""Durable storage for explicitly redacted controlled-run report snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cortex.db.models import DemoRunReportRecord

from .contracts import DemoRunReport


class DemoRunReportProjectionError(RuntimeError):
    """A durable demo-run report is invalid or conflicts with its identity."""


def stable_demo_run_report_id(workspace_id: str, run_id_hash: str) -> str:
    """Return a bounded internal ID without introducing a raw run identifier."""
    digest = sha256(f"{workspace_id}:{run_id_hash}".encode()).hexdigest()
    return f"drpt_{digest}"


class SqlAlchemyDemoRunReportRepository:
    """Caller-owned SQL repository for immutable redacted run reports.

    No method here performs provider, Qdrant, or retrieval calls. A trusted
    finalizer supplies an already-validated aggregate report after it has
    established the exact controlled-run membership. Direct database changes
    are treated as untrusted on read and fail closed.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_report(
        self,
        *,
        workspace_id: str,
        source_connection_id: str,
        report: DemoRunReport,
        completed_at: datetime | None = None,
    ) -> DemoRunReport:
        """Persist one immutable snapshot, accepting only an identical replay."""
        if not workspace_id or len(workspace_id) > 128:
            raise ValueError("workspace_id must be between 1 and 128 characters")
        if not source_connection_id or len(source_connection_id) > 128:
            raise ValueError(
                "source_connection_id must be between 1 and 128 characters"
            )
        if completed_at is not None and completed_at.tzinfo is None:
            raise ValueError("completed_at must be timezone-aware")

        report_id = stable_demo_run_report_id(workspace_id, report.run_id_hash)
        existing = await self.session.get(DemoRunReportRecord, report_id)
        if existing is not None:
            return _identical_report_or_raise(
                existing,
                workspace_id=workspace_id,
                source_connection_id=source_connection_id,
                report=report,
            )

        now = datetime.now(UTC)
        record = DemoRunReportRecord(
            id=report_id,
            workspace_id=workspace_id,
            source_connection_id=source_connection_id,
            provider=report.provider,
            run_id_hash=report.run_id_hash,
            source_ref_hash=report.source_ref_hash,
            collection=report.collection,
            outcome=report.outcome,
            report_json=report.model_dump(mode="json"),
            completed_at=completed_at or now,
            created_at=now,
        )
        # The deterministic record ID plus the unique workspace/run constraint
        # makes a retry idempotent. A savepoint leaves the caller's broader
        # transaction usable if a concurrent finalizer wins the insert.
        try:
            async with self.session.begin_nested():
                self.session.add(record)
                await self.session.flush()
        except IntegrityError:
            existing = await self.session.get(DemoRunReportRecord, report_id)
            if existing is None:
                existing = await self._find_by_workspace_run(
                    workspace_id=workspace_id,
                    run_id_hash=report.run_id_hash,
                )
            if existing is None:
                raise
            return _identical_report_or_raise(
                existing,
                workspace_id=workspace_id,
                source_connection_id=source_connection_id,
                report=report,
            )
        return report

    async def latest_report(self, *, workspace_id: str) -> DemoRunReport | None:
        """Return the newest valid snapshot for exactly one workspace.

        A corrupt newest row deliberately returns ``None`` instead of falling
        back to a prior report. That prevents a stale/forged record from being
        presented as current live evidence.
        """
        result = await self.session.execute(
            select(DemoRunReportRecord)
            .where(DemoRunReportRecord.workspace_id == workspace_id)
            .order_by(
                DemoRunReportRecord.completed_at.desc(),
                DemoRunReportRecord.created_at.desc(),
                DemoRunReportRecord.id.desc(),
            )
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        try:
            return _validated_report_from_record(record, workspace_id=workspace_id)
        except DemoRunReportProjectionError:
            return None

    async def _find_by_workspace_run(
        self, *, workspace_id: str, run_id_hash: str
    ) -> DemoRunReportRecord | None:
        result = await self.session.execute(
            select(DemoRunReportRecord).where(
                DemoRunReportRecord.workspace_id == workspace_id,
                DemoRunReportRecord.run_id_hash == run_id_hash,
            )
        )
        return result.scalar_one_or_none()


def _validated_report_from_record(
    record: DemoRunReportRecord, *, workspace_id: str
) -> DemoRunReport:
    if record.workspace_id != workspace_id:
        raise DemoRunReportProjectionError("workspace mismatch")
    try:
        report = DemoRunReport.model_validate(record.report_json)
    except (TypeError, ValidationError, ValueError) as error:
        raise DemoRunReportProjectionError(
            "stored report is not a valid v1 snapshot"
        ) from error
    if (
        record.id != stable_demo_run_report_id(workspace_id, report.run_id_hash)
        or record.provider != report.provider
        or record.run_id_hash != report.run_id_hash
        or record.source_ref_hash != report.source_ref_hash
        or record.collection != report.collection
        or record.outcome != report.outcome
    ):
        raise DemoRunReportProjectionError("stored report metadata mismatch")
    return report


def _identical_report_or_raise(
    record: DemoRunReportRecord,
    *,
    workspace_id: str,
    source_connection_id: str,
    report: DemoRunReport,
) -> DemoRunReport:
    persisted = _validated_report_from_record(record, workspace_id=workspace_id)
    if record.source_connection_id != source_connection_id or persisted != report:
        raise DemoRunReportProjectionError("immutable run report conflict")
    return persisted
