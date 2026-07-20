"""Normalization for the bounded Jira offline snapshot contract."""

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
    optional_str,
    parse_datetime,
    required_str,
)

NORMALIZED_VERSION = "jira-snapshot-normalizer-v1"
SUPPORTED_EVENT_TYPES = {"jira.issue.snapshot"}


def normalize_jira_payload(
    raw_event: RawEvent, payload_bytes: bytes
) -> NormalizationResult:
    if raw_event.event_type not in SUPPORTED_EVENT_TYPES:
        raise ProviderNormalizationError("unsupported jira event type")
    payload = load_object(payload_bytes, "jira")
    if payload.get("connector_mode") != "planned_snapshot":
        raise ProviderNormalizationError("jira payload is not a planned snapshot")
    issue = _issue_payload(payload)
    issue_id = required_str(issue, "id", "jira")
    issue_key = required_str(issue, "key", "jira")
    title = required_str(issue, "title", "jira")
    description = optional_str(issue, "description") or ""
    content_text = "\n\n".join(
        part for part in (f"{issue_key}: {title}", description) if part
    )
    updated_at = parse_datetime(issue.get("updated_at")) or raw_event.occurred_at
    now = datetime.now(UTC)
    source_object = SourceObject(
        id=stable_id("so", raw_event.workspace_id, "jira", "jira_issue", issue_id),
        workspace_id=raw_event.workspace_id,
        source_connection_id=raw_event.source_connection_id,
        provider="jira",
        object_type="jira_issue",
        external_object_id=issue_id,
        external_object_key=f"jira:{issue_key}",
        title=f"{issue_key}: {title}",
        canonical_url=optional_str(issue, "url"),
        occurred_at=updated_at,
        source_updated_at=updated_at,
        normalized_version=NORMALIZED_VERSION,
        content_hash=sha256_digest(content_text.encode()),
        content_text=content_text,
        metadata_json={
            "source_kind": "jira_issue",
            "issue_key": issue_key,
            "project_id": optional_str(issue, "project_id"),
            "status": optional_str(issue, "status"),
        },
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


def _issue_payload(payload: dict[str, Any]) -> dict[str, Any]:
    issue = payload.get("issue")
    if not isinstance(issue, dict):
        raise ProviderNormalizationError("jira issue payload must be an object")
    return issue
