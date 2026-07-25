from __future__ import annotations

from datetime import UTC, datetime

from cortex.contracts.entities import RawEvent, SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.ingestion.payloads import sha256_digest
from cortex.normalization.normalizers.fixtures import (
    normalize_fixture_payload,
    stable_id,
)
from cortex.normalization.result import NormalizationResult

from .provider_payloads import load_object, optional_str, parse_datetime, required_str

NORMALIZED_VERSION = "repo-docs-normalizer-v1"


def normalize_repo_doc_payload(
    raw_event: RawEvent, payload_bytes: bytes
) -> NormalizationResult:
    payload = load_object(payload_bytes, "repo_docs")
    if "fixture_id" in payload:
        return normalize_fixture_payload(raw_event, payload_bytes)
    repo_id = required_str(payload, "repo_id", "repo_docs")
    path = required_str(payload, "path", "repo_docs")
    content = required_str(payload, "content", "repo_docs")
    title = optional_str(payload, "title") or path.rsplit("/", 1)[-1]
    now = datetime.now(UTC)
    updated_at = parse_datetime(payload.get("updated_at")) or raw_event.occurred_at
    status = (
        SourceObjectStatus.DELETED
        if payload.get("operation") == "deleted"
        else SourceObjectStatus.ACTIVE
    )
    source_object = SourceObject(
        id=stable_id(
            "so", raw_event.workspace_id, "repo_docs", "repo_doc", repo_id, path
        ),
        workspace_id=raw_event.workspace_id,
        source_connection_id=raw_event.source_connection_id,
        provider="repo_docs",
        object_type="repo_doc",
        external_object_id=f"{repo_id}:{path}",
        external_object_key=f"doc:{repo_id}:{path}",
        title=title,
        canonical_url=optional_str(payload, "canonical_url"),
        occurred_at=updated_at,
        source_updated_at=updated_at,
        normalized_version=NORMALIZED_VERSION,
        content_hash=sha256_digest(content.encode()),
        content_text=content,
        metadata_json={
            "source_kind": "repo_doc",
            "repo_id": repo_id,
            "path": path,
            "ref": optional_str(payload, "ref"),
            "operation": optional_str(payload, "operation") or "imported",
            "is_stale": bool(payload.get("is_stale", False)),
        },
        status=SourceObjectStatus.STALE if payload.get("is_stale", False) else status,
        trace_id=raw_event.trace_id,
        created_at=now,
        updated_at=now,
        deleted_at=now if status == SourceObjectStatus.DELETED else None,
    )
    return NormalizationResult(
        raw_event_id=raw_event.id,
        normalized_version=NORMALIZED_VERSION,
        source_objects=[source_object],
    )
