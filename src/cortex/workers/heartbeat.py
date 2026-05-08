from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True)
class WorkerHeartbeat:
    role: str
    instance_id: str
    status: str
    last_heartbeat_at: datetime
    failure_reason: str | None = None

    def safe_summary(self) -> dict[str, str]:
        summary = {
            "role": self.role,
            "instance_id": self.instance_id,
            "status": self.status,
            "last_heartbeat_at": self.last_heartbeat_at.isoformat(),
        }
        if self.failure_reason:
            summary["failure_reason"] = self.failure_reason
        return summary


class InMemoryWorkerHeartbeatRepository:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], WorkerHeartbeat] = {}

    def record(
        self,
        *,
        role: str,
        instance_id: str,
        status: str,
        failure_reason: str | None = None,
    ) -> WorkerHeartbeat:
        heartbeat = WorkerHeartbeat(
            role=role,
            instance_id=instance_id,
            status=status,
            failure_reason=failure_reason,
            last_heartbeat_at=datetime.now(UTC),
        )
        self._records[(role, instance_id)] = heartbeat
        return heartbeat

    def list_all(self) -> list[WorkerHeartbeat]:
        return list(self._records.values())


def default_worker_instance_id(role: str) -> str:
    return f"{role}-{uuid4().hex[:12]}"
