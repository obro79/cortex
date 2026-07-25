from __future__ import annotations

from datetime import UTC, datetime

from cortex.contracts.entities import AuditLog
from cortex.ingestion.payloads import sha256_digest
from cortex.security.redaction import redact_mapping


class InMemoryAuditLogRepository:
    def __init__(self) -> None:
        self._records: list[AuditLog] = []

    def append(
        self,
        *,
        workspace_id: str,
        action: str,
        decision: str,
        actor_id: str | None = None,
        target_type: str,
        target_id: str | None = None,
        reason: str | None = None,
        metadata_json: dict[str, object] | None = None,
        trace_id: str | None = None,
    ) -> AuditLog:
        now = datetime.now(UTC)
        target_id_hash = sha256_digest(target_id.encode()) if target_id else None
        sequence = len(self._records) + 1
        record = AuditLog(
            id=f"audit_{sequence:08d}",
            workspace_id=workspace_id,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id_hash=target_id_hash,
            decision=decision,
            reason=reason,
            metadata_json=redact_mapping(metadata_json or {}),
            trace_id=trace_id,
            created_at=now,
        )
        self._records.append(record)
        return record

    def list_for_workspace(self, workspace_id: str) -> list[AuditLog]:
        return [
            record for record in self._records if record.workspace_id == workspace_id
        ]
