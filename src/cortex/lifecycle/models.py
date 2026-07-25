from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class LifecycleActionStatus(StrEnum):
    REQUESTED = "requested"
    VALIDATED = "validated"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass(frozen=True)
class RetentionPolicy:
    workspace_id: str
    raw_event_days: int | None = 365
    payload_days: int | None = 90
    audit_log_days: int | None = None
    tombstone_days: int | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class DeletionTombstone:
    id: str
    workspace_id: str
    target_type: str
    target_id_hash: str
    status: LifecycleActionStatus
    requested_by_user_id: str
    reason: str
    created_at: datetime
    completed_at: datetime | None = None
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ExportJob:
    id: str
    workspace_id: str
    requested_by_user_id: str
    status: LifecycleActionStatus
    export_scope: str
    destination_ref: str | None
    created_at: datetime
    completed_at: datetime | None = None
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RetentionSweepPlan:
    workspace_id: str
    raw_events_before: datetime | None
    payloads_before: datetime | None
    audit_logs_before: datetime | None
    tombstones_before: datetime | None
