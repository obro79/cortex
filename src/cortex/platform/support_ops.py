from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cortex.security.admin_auth import AdminActor, AdminAuthorizationService

SupportOperation = Literal[
    "connector_resync",
    "deadletter_replay",
    "force_reembed",
    "force_reindex",
    "source_health_inspect",
]


@dataclass(frozen=True)
class SupportOperationResult:
    ok: bool
    operation: SupportOperation
    status: Literal["accepted", "denied"]
    reason: str
    target_type: str
    target_id: str


class SupportOpsService:
    def __init__(self, authorization: AdminAuthorizationService) -> None:
        self.authorization = authorization

    def request_operation(
        self,
        *,
        workspace_id: str,
        actor: AdminActor | None,
        operation: SupportOperation,
        target_type: str,
        target_id: str,
        trace_id: str | None = None,
    ) -> SupportOperationResult:
        auth = self.authorization.require_admin(
            workspace_id=workspace_id,
            actor=actor,
            action=f"support_ops.{operation}",
            target_type=target_type,
            target_id=target_id,
            metadata_json={
                "operation": operation,
                "trace_id": trace_id,
            },
        )
        return SupportOperationResult(
            ok=auth.allowed,
            operation=operation,
            status="accepted" if auth.allowed else "denied",
            reason=auth.reason,
            target_type=target_type,
            target_id=target_id,
        )

    def connector_resync(
        self, *, workspace_id: str, actor: AdminActor | None, source_connection_id: str
    ) -> SupportOperationResult:
        return self.request_operation(
            workspace_id=workspace_id,
            actor=actor,
            operation="connector_resync",
            target_type="source_connection",
            target_id=source_connection_id,
        )

    def deadletter_replay(
        self, *, workspace_id: str, actor: AdminActor | None, raw_event_id: str
    ) -> SupportOperationResult:
        return self.request_operation(
            workspace_id=workspace_id,
            actor=actor,
            operation="deadletter_replay",
            target_type="raw_event",
            target_id=raw_event_id,
        )

    def force_reembed(
        self, *, workspace_id: str, actor: AdminActor | None, source_chunk_id: str
    ) -> SupportOperationResult:
        return self.request_operation(
            workspace_id=workspace_id,
            actor=actor,
            operation="force_reembed",
            target_type="source_chunk",
            target_id=source_chunk_id,
        )

    def force_reindex(
        self, *, workspace_id: str, actor: AdminActor | None, source_object_id: str
    ) -> SupportOperationResult:
        return self.request_operation(
            workspace_id=workspace_id,
            actor=actor,
            operation="force_reindex",
            target_type="source_object",
            target_id=source_object_id,
        )

    def inspect_source_health(
        self, *, workspace_id: str, actor: AdminActor | None, source_connection_id: str
    ) -> SupportOperationResult:
        return self.request_operation(
            workspace_id=workspace_id,
            actor=actor,
            operation="source_health_inspect",
            target_type="source_connection",
            target_id=source_connection_id,
        )
