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

NORMALIZED_VERSION = "github-normalizer-v1"


def normalize_github_payload(
    raw_event: RawEvent, payload_bytes: bytes
) -> NormalizationResult:
    payload = load_object(payload_bytes, "github")
    if "fixture_id" in payload:
        return normalize_fixture_payload(raw_event, payload_bytes)
    kind, item = _github_item(payload)
    repo = _repo_payload(payload)
    repo_id = str(repo.get("id") or payload.get("repository_id") or "unknown-repo")
    number = item.get("number")
    sha = item.get("sha")
    external_id = str(item.get("id") or sha or number or raw_event.external_event_id)
    title = _title(kind, item, external_id)
    body = optional_str(item, "body") or optional_str(item, "message") or ""
    comments = _body_list(payload, "comments") + _body_list(payload, "reviews")
    changed_files = [
        str(file.get("filename"))
        for file in optional_list(payload, "changed_files")
        if isinstance(file, dict) and file.get("filename")
    ]
    content_parts = [title]
    if body:
        content_parts.append(body)
    if comments:
        content_parts.append("\n".join(comments))
    if changed_files:
        content_parts.append("Changed files:\n" + "\n".join(changed_files))
    content_text = "\n\n".join(content_parts)
    object_type = {
        "pull_request": "github_pull_request",
        "issue": "github_issue",
        "commit": "github_commit",
    }[kind]
    now = datetime.now(UTC)
    occurred_at = (
        parse_datetime(item.get("updated_at"))
        or parse_datetime(item.get("created_at"))
        or parse_datetime(item.get("timestamp"))
        or raw_event.occurred_at
    )
    source_object = SourceObject(
        id=stable_id("so", raw_event.workspace_id, "github", object_type, external_id),
        workspace_id=raw_event.workspace_id,
        source_connection_id=raw_event.source_connection_id,
        provider="github",
        object_type=object_type,
        external_object_id=external_id,
        external_object_key=f"github:{repo_id}:{kind}:{number or sha or external_id}",
        title=title,
        canonical_url=optional_str(item, "html_url"),
        author_external_id=_user_id(item.get("user") or item.get("author")),
        occurred_at=occurred_at,
        source_updated_at=occurred_at,
        normalized_version=NORMALIZED_VERSION,
        content_hash=sha256_digest(content_text.encode()),
        content_text=content_text,
        metadata_json={
            "source_kind": object_type,
            "repo_id": repo_id,
            "repo_name_hash": sha256_digest(
                str(repo.get("full_name", repo_id)).encode()
            ),
            "number": number,
            "sha": sha,
            "comment_count": len(comments),
            "changed_file_count": len(changed_files),
            "changed_file_paths": changed_files,
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


def _github_item(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    for key in ("pull_request", "issue", "commit"):
        value = payload.get(key)
        if isinstance(value, dict):
            return key, value
    kind = payload.get("object_kind")
    if kind in {"pull_request", "issue", "commit"}:
        return str(kind), payload
    raise ProviderNormalizationError(
        "github payload missing pull_request, issue, or commit"
    )


def _repo_payload(payload: dict[str, Any]) -> dict[str, Any]:
    repo = payload.get("repository", {})
    if repo is None:
        return {}
    if not isinstance(repo, dict):
        raise ProviderNormalizationError("github repository payload must be an object")
    return repo


def _title(kind: str, item: dict[str, Any], external_id: str) -> str:
    if kind == "commit":
        message = optional_str(item, "message") or external_id
        return message.splitlines()[0]
    return required_str(item, "title", "github")


def _body_list(payload: dict[str, Any], key: str) -> list[str]:
    bodies = []
    for item in optional_list(payload, key):
        if isinstance(item, dict):
            body = item.get("body")
            if isinstance(body, str) and body:
                bodies.append(body)
    return bodies


def _user_id(value: object) -> str | None:
    if isinstance(value, dict):
        user_id = value.get("id") or value.get("login")
        return str(user_id) if user_id else None
    return None
