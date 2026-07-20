"""Safe control-plane contracts for demo runs and per-source health.

``DemoRunReport`` serializes to the persisted
``live-context-run-report/v1`` schema validated by the operator preflight.
It intentionally permits only aggregate counts and opaque hashes.  The
separate source-health DTO is likewise content-free.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceMode = Literal["live", "imported_snapshot", "fixture"]
Readiness = Literal["ready", "partial", "not_ready", "unavailable"]
Freshness = Literal["fresh", "stale", "unknown"]
Outcome = Literal["passed", "failed", "partial"]
IssueSeverity = Literal["warning", "error"]
type OpaqueHash = Annotated[
    str,
    Field(
        min_length=71,
        max_length=71,
        pattern=r"^sha256:[A-Fa-f0-9]{64}$",
    ),
]
type StageCode = Annotated[
    str,
    Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_:-]*$"),
]
_URL_LIKE = re.compile(r"(?:[a-z][a-z0-9+.-]*://|www\.)", re.IGNORECASE)


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LiveRunCounts(_ContractModel):
    """The exact aggregate count set permitted in a persisted run report."""

    raw_events: int = Field(ge=0)
    source_objects: int = Field(ge=0)
    source_chunks: int = Field(ge=0)
    embeddings_completed: int = Field(ge=0)
    vector_points_verified: int = Field(ge=0)
    query_requests: int = Field(ge=0)
    evidence_packs: int = Field(ge=0)
    failures: int = Field(ge=0)


class ReportIssue(_ContractModel):
    """A stable safe code only; protected detail belongs in operational logs."""

    code: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9_:-]+$")
    severity: IssueSeverity


class SourceHealth(_ContractModel):
    """Per-source aggregate status. Raw source identifiers never leave storage."""

    source_ref_hash: OpaqueHash
    provider: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_-]+$")
    mode: SourceMode
    readiness: Readiness
    freshness: Freshness
    freshness_seconds: int | None = Field(default=None, ge=0)
    counts: LiveRunCounts
    warnings: tuple[ReportIssue, ...] = ()
    errors: tuple[ReportIssue, ...] = ()


class DemoRunReport(_ContractModel):
    """Persistable redacted run report for the live-context-run-report schema."""

    schema_version: Literal["live-context-run-report/v1"] = "live-context-run-report/v1"
    mode: Literal["controlled_live_run"]
    outcome: Outcome
    live_data: Literal[True]
    run_id_hash: OpaqueHash
    environment: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_-]+$")
    provider: Literal["slack"]
    source_ref_hash: OpaqueHash
    collection: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_.-]+$")
    counts: LiveRunCounts
    freshness_seconds: int | None = Field(default=None, ge=0)
    stages: dict[StageCode, StageCode] = Field(min_length=1, max_length=40)
    disclosure: str = Field(min_length=1, max_length=400)
    next_action: str | None = Field(default=None, max_length=400)

    @field_validator("disclosure", "next_action")
    @classmethod
    def _safe_display_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if "\n" in value or "\r" in value or _URL_LIKE.search(value):
            raise ValueError("must not contain a newline or URL-like value")
        return value


class DemoRunReportStatus(_ContractModel):
    """A typed read result; unavailable is explicit rather than fabricated."""

    contract_version: Literal["cortex.demo_run_report_status.v1"] = (
        "cortex.demo_run_report_status.v1"
    )
    trace_id_hash: OpaqueHash
    available: bool
    report: DemoRunReport | None
    issues: tuple[ReportIssue, ...] = ()


class SourceHealthStatus(_ContractModel):
    """Source-only projection; no raw IDs, URLs, text, or secrets."""

    contract_version: Literal["cortex.source_health.v1"] = "cortex.source_health.v1"
    trace_id_hash: OpaqueHash
    available: bool
    readiness: Readiness
    freshness: Freshness
    sources: tuple[SourceHealth, ...] = ()
    issues: tuple[ReportIssue, ...] = ()
