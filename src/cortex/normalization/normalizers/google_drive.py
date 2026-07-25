"""Normalization for the bounded Google Drive offline snapshot contract."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cortex.contracts.entities import RawEvent, SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.ingestion.payloads import sha256_digest
from cortex.normalization.normalizers.fixtures import stable_id
from cortex.normalization.result import NormalizationResult

from .provider_payloads import (
    ProviderNormalizationError,
    load_object,
    optional_list,
    optional_str,
    parse_datetime,
    required_str,
)

NORMALIZED_VERSION = "google-drive-snapshot-normalizer-v1"
SUPPORTED_EVENT_TYPES = {"google_drive.file.snapshot"}


def normalize_google_drive_payload(
    raw_event: RawEvent, payload_bytes: bytes
) -> NormalizationResult:
    if raw_event.event_type not in SUPPORTED_EVENT_TYPES:
        raise ProviderNormalizationError("unsupported google drive event type")
    payload = load_object(payload_bytes, "google_drive")
    if payload.get("connector_mode") != "planned_snapshot":
        raise ProviderNormalizationError(
            "google drive payload is not a planned snapshot"
        )
    file = _file_payload(payload)
    file_id = required_str(file, "id", "google_drive")
    name = required_str(file, "name", "google_drive")
    mime_type = required_str(file, "mime_type", "google_drive")
    description = optional_str(file, "description") or ""
    content_text = "\n\n".join(part for part in (name, description) if part)
    updated_at = parse_datetime(file.get("modified_at")) or raw_event.occurred_at
    parent_ids = [
        value for value in optional_list(file, "parent_ids") if isinstance(value, str)
    ]
    now = datetime.now(UTC)
    source_object = SourceObject(
        id=stable_id(
            "so", raw_event.workspace_id, "google_drive", "drive_file", file_id
        ),
        workspace_id=raw_event.workspace_id,
        source_connection_id=raw_event.source_connection_id,
        provider="google_drive",
        object_type="drive_file",
        external_object_id=file_id,
        external_object_key=f"google_drive:file:{file_id}",
        title=name,
        canonical_url=optional_str(file, "web_url"),
        occurred_at=updated_at,
        source_updated_at=updated_at,
        normalized_version=NORMALIZED_VERSION,
        content_hash=sha256_digest(content_text.encode()),
        content_text=content_text,
        metadata_json={
            "source_kind": "drive_file",
            "mime_type": mime_type,
            "parent_ids": parent_ids,
            "trashed": file.get("trashed") is True,
        },
        status=SourceObjectStatus.DELETED
        if file.get("trashed") is True
        else SourceObjectStatus.ACTIVE,
        trace_id=raw_event.trace_id,
        created_at=now,
        updated_at=now,
        deleted_at=now if file.get("trashed") is True else None,
    )
    return NormalizationResult(
        raw_event_id=raw_event.id,
        normalized_version=NORMALIZED_VERSION,
        source_objects=[source_object],
    )


def _file_payload(payload: dict[str, Any]) -> dict[str, Any]:
    file = payload.get("file")
    if not isinstance(file, dict):
        raise ProviderNormalizationError("google drive file payload must be an object")
    return file
