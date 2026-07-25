"""Normalize explicit structured agent checkpoint exports only."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cortex.contracts.agent_sessions import (
    EXPORT_MARKER,
    AgentCheckpointExport,
)
from cortex.contracts.entities import RawEvent, SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.normalization.normalizers.fixtures import stable_id
from cortex.normalization.normalizers.provider_payloads import (
    ProviderNormalizationError,
    load_object,
)
from cortex.normalization.result import NormalizationResult

NORMALIZED_VERSION = "agent-checkpoint-normalizer-v1"
SUPPORTED_EVENT_TYPES = {"agent_session.checkpoint.exported"}


def normalize_agent_session_payload(
    raw_event: RawEvent, payload_bytes: bytes
) -> NormalizationResult:
    if raw_event.event_type not in SUPPORTED_EVENT_TYPES:
        raise ProviderNormalizationError("unsupported agent session event type")
    payload = load_object(payload_bytes, "agent_session")
    export, local_session_ref_hash = _parse_export(payload)
    checkpoint = export.content_payload()
    now = datetime.now(UTC)
    checkpoint_id = export.checkpoint_id
    source_object = SourceObject(
        id=stable_id("so", raw_event.workspace_id, "agent_session", checkpoint_id),
        workspace_id=raw_event.workspace_id,
        source_connection_id=raw_event.source_connection_id,
        provider="agent_session",
        object_type="agent_checkpoint",
        external_object_id=checkpoint_id,
        external_object_key=f"agent_session:checkpoint:{checkpoint_id}",
        title=_title(checkpoint),
        occurred_at=raw_event.occurred_at or raw_event.received_at,
        source_updated_at=raw_event.occurred_at or raw_event.received_at,
        normalized_version=NORMALIZED_VERSION,
        content_hash=export.content_hash,
        content_text=_content_text(checkpoint),
        metadata_json=_metadata(export, checkpoint, local_session_ref_hash),
        status=SourceObjectStatus.ACTIVE,
        trace_id=raw_event.trace_id,
        created_at=now,
        updated_at=now,
    )
    return NormalizationResult(
        raw_event_id=raw_event.id,
        normalized_version=NORMALIZED_VERSION,
        source_objects=[source_object],
    )


def _parse_export(payload: dict[str, Any]) -> tuple[AgentCheckpointExport, str]:
    if payload.get("export_marker") != EXPORT_MARKER:
        raise ProviderNormalizationError(
            "agent checkpoint requires explicit export marker"
        )
    if payload.get("export_enabled") is not True:
        raise ProviderNormalizationError(
            "agent checkpoint export is not explicitly enabled"
        )
    checkpoint = payload.get("checkpoint")
    local_ref_hash = payload.get("local_session_ref_hash")
    if (
        not isinstance(checkpoint, dict)
        or not isinstance(local_ref_hash, str)
        or not local_ref_hash.startswith("sha256:")
        or len(local_ref_hash) != 71
    ):
        raise ProviderNormalizationError("agent checkpoint payload is malformed")
    try:
        return (
            AgentCheckpointExport(
                export_marker=payload["export_marker"],
                export_enabled=payload["export_enabled"],
                local_session_ref="x" * 16,
                content_hash=payload["content_hash"],
                **checkpoint,
            ),
            local_ref_hash,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ProviderNormalizationError(
            "agent checkpoint export validation failed"
        ) from error


def _title(checkpoint: dict[str, Any]) -> str:
    return f"Agent checkpoint: {checkpoint['task_state']}"


def _content_text(checkpoint: dict[str, Any]) -> str:
    sections = [
        f"Task state: {checkpoint['task_state']}",
        f"Task summary: {checkpoint['task_summary']}",
    ]
    for decision in checkpoint["decisions"]:
        sections.append(f"Decision: {decision['summary']}")
    for file in checkpoint["files"]:
        path = "[sensitive path redacted]" if _file_is_sensitive(file) else file["path"]
        sections.append(f"File: {path} — {file['summary']}")
    for command in checkpoint["commands"]:
        sections.append(f"Command: {command['summary']}")
    for test in checkpoint["tests"]:
        sections.append(f"Test: {test['summary']}")
    sections.extend(f"Next action: {action}" for action in checkpoint["next_actions"])
    sections.extend(
        f"Evidence: {evidence['label']} ({evidence['reference']})"
        for evidence in checkpoint["evidence_references"]
    )
    return "\n\n".join(sections)


def _metadata(
    export: AgentCheckpointExport,
    checkpoint: dict[str, Any],
    local_session_ref_hash: str,
) -> dict[str, Any]:
    return {
        "source_kind": "explicit_agent_checkpoint_export",
        "provider": str(export.provider),
        "visibility": str(export.visibility),
        "local_session_ref_hash": local_session_ref_hash,
        "file_summaries": [
            {
                "path_hash": _path_hash(file["path"]),
                "sensitive_path": _file_is_sensitive(file),
            }
            for file in checkpoint["files"]
        ],
        "evidence_references": [
            {"label": evidence["label"], "reference": evidence["reference"]}
            for evidence in checkpoint["evidence_references"]
        ],
        "deletion_revocation_supported": True,
        "transcript_capture": "not_supported",
    }


def _file_is_sensitive(file: dict[str, Any]) -> bool:
    return bool(file["sensitive_path"]) or any(
        part in file["path"].lower()
        for part in (
            ".env",
            ".pem",
            ".key",
            "credential",
            "secret",
            "token",
            "id_rsa",
            "private",
        )
    )


def _path_hash(path: str) -> str:
    from cortex.ingestion.payloads import sha256_digest

    return sha256_digest(path.encode())
