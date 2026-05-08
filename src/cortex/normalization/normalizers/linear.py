from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cortex.contracts.entities import RawEvent, SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.ingestion.payloads import sha256_digest
from cortex.normalization.normalizers.fixtures import (
    normalize_fixture_payload,
    stable_id,
)
from cortex.normalization.result import NormalizationResult

from .provider_payloads import (
    ProviderNormalizationError,
    load_object,
    optional_list,
    optional_str,
    parse_datetime,
    required_str,
)

NORMALIZED_VERSION = "linear-normalizer-v1"


def normalize_linear_payload(
    raw_event: RawEvent, payload_bytes: bytes
) -> NormalizationResult:
    payload = load_object(payload_bytes, "linear")
    if "fixture_id" in payload:
        return normalize_fixture_payload(raw_event, payload_bytes)
    issue = _issue_payload(payload)
    issue_id = required_str(issue, "id", "linear")
    identifier = optional_str(issue, "identifier") or issue_id
    title = required_str(issue, "title", "linear")
    description = optional_str(issue, "description") or ""
    comments = _comment_texts(issue)
    content_parts = [f"{identifier}: {title}"]
    if description:
        content_parts.append(description)
    if comments:
        content_parts.append("\n".join(comments))
    content_text = "\n\n".join(content_parts)
    now = datetime.now(UTC)
    occurred_at = (
        parse_datetime(issue.get("updatedAt"))
        or parse_datetime(issue.get("createdAt"))
        or raw_event.occurred_at
    )
    project = _nested_id(issue.get("project"))
    team = _nested_id(issue.get("team"))
    status = _nested_name(issue.get("state"))
    labels = [
        str(label.get("id"))
        for label in optional_list(issue, "labels")
        if isinstance(label, dict) and label.get("id")
    ]
    source_object = SourceObject(
        id=stable_id("so", raw_event.workspace_id, "linear", "linear_issue", issue_id),
        workspace_id=raw_event.workspace_id,
        source_connection_id=raw_event.source_connection_id,
        provider="linear",
        object_type="linear_issue",
        external_object_id=issue_id,
        external_object_key=f"linear:{identifier}",
        title=f"{identifier}: {title}",
        canonical_url=optional_str(issue, "url"),
        author_external_id=_nested_id(issue.get("creator")),
        occurred_at=occurred_at,
        source_updated_at=occurred_at,
        normalized_version=NORMALIZED_VERSION,
        content_hash=sha256_digest(content_text.encode()),
        content_text=content_text,
        metadata_json={
            "source_kind": "linear_issue",
            "identifier": identifier,
            "team_id": team,
            "project_id": project,
            "status": status,
            "assignee_id": _nested_id(issue.get("assignee")),
            "label_ids": labels,
            "comment_count": len(comments),
            "has_blockers": bool(issue.get("relations") or issue.get("blockedBy")),
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
    value = payload.get("issue", payload)
    if not isinstance(value, dict):
        raise ProviderNormalizationError("linear issue payload must be an object")
    return value


def _comment_texts(issue: dict[str, Any]) -> list[str]:
    comments = []
    for comment in optional_list(issue, "comments"):
        if isinstance(comment, dict):
            body = comment.get("body")
            if isinstance(body, str) and body:
                comments.append(body)
    return comments


def _nested_id(value: object) -> str | None:
    if isinstance(value, dict):
        nested = value.get("id")
        return str(nested) if nested else None
    return None


def _nested_name(value: object) -> str | None:
    if isinstance(value, dict):
        nested = value.get("name")
        return str(nested) if nested else None
    return None
