"""Redacted demo-run reporting contracts and credential-free adapters."""

from .contracts import (
    DemoRunReport,
    DemoRunReportStatus,
    LiveRunCounts,
    ReportIssue,
    SourceHealth,
    SourceHealthStatus,
)
from .service import DemoRunReportReader, FixtureDemoRunReportReader, SourceHealthReader

__all__ = [
    "DemoRunReport",
    "DemoRunReportReader",
    "DemoRunReportStatus",
    "FixtureDemoRunReportReader",
    "LiveRunCounts",
    "ReportIssue",
    "SourceHealth",
    "SourceHealthReader",
    "SourceHealthStatus",
]
