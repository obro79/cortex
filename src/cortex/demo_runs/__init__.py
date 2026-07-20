"""Redacted demo-run reporting contracts and credential-free adapters."""

from .contracts import (
    DemoRunReport,
    DemoRunReportStatus,
    LiveRunCounts,
    ReportIssue,
    SourceHealth,
    SourceHealthStatus,
)
from .repositories import (
    DemoRunReportProjectionError,
    SqlAlchemyDemoRunReportRepository,
    stable_demo_run_report_id,
)
from .service import (
    DemoRunReportReader,
    FixtureDemoRunReportReader,
    SourceHealthReader,
    SqlAlchemyDemoRunReportStore,
)

__all__ = [
    "DemoRunReport",
    "DemoRunReportProjectionError",
    "DemoRunReportReader",
    "DemoRunReportStatus",
    "FixtureDemoRunReportReader",
    "LiveRunCounts",
    "ReportIssue",
    "SourceHealth",
    "SourceHealthReader",
    "SourceHealthStatus",
    "SqlAlchemyDemoRunReportRepository",
    "SqlAlchemyDemoRunReportStore",
    "stable_demo_run_report_id",
]
