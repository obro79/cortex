from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from cortex.contracts.entities import RawEvent, SourceFile, SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.ingestion.payloads import sha256_digest
from cortex.normalization.result import NormalizationResult, RelationshipSeed

NORMALIZED_VERSION = "fixture-normalizer-v1"


class FixtureNormalizationError(Exception):
    pass


def stable_id(prefix: str, *parts: str) -> str:
    digest = sha256_digest("|".join(parts).encode()).removeprefix("sha256:")[:24]
    return f"{prefix}_{digest}"


def normalize_fixture_payload(
    raw_event: RawEvent, payload_bytes: bytes
) -> NormalizationResult:
    payload = _load_payload(payload_bytes)
    fixture_id = _required_str(payload, "fixture_id")
    provider = _required_str(payload, "provider")
    object_type = _required_str(payload, "object_type")
    title = _required_str(payload, "title")
    content = _required_str(payload, "content")
    source_kind = _required_str(payload, "source_kind")
    canonical_url = _optional_str(payload, "canonical_url")
    occurred_at = _parse_datetime(payload.get("occurred_at")) or raw_event.occurred_at
    external_object_id = _optional_str(payload, "external_object_id") or fixture_id
    external_object_key = f"{provider}:{fixture_id}"
    source_object_id = stable_id(
        "so",
        raw_event.workspace_id,
        provider,
        object_type,
        external_object_id,
    )
    now = datetime.now(UTC)
    content_hash = sha256_digest(content.encode())
    source_object = SourceObject(
        id=source_object_id,
        workspace_id=raw_event.workspace_id,
        source_connection_id=raw_event.source_connection_id,
        provider=provider,
        object_type=object_type,
        external_object_id=external_object_id,
        external_object_key=external_object_key,
        title=title,
        canonical_url=canonical_url,
        occurred_at=occurred_at,
        source_updated_at=occurred_at,
        normalized_version=NORMALIZED_VERSION,
        content_hash=content_hash,
        metadata_json={
            "fixture_id": fixture_id,
            "source_kind": source_kind,
            "is_stale": bool(payload.get("is_stale", False)),
        },
        status=SourceObjectStatus.STALE
        if payload.get("is_stale", False)
        else SourceObjectStatus.ACTIVE,
        trace_id=raw_event.trace_id,
        created_at=now,
        updated_at=now,
    )
    source_files = _source_files(raw_event, payload, source_object, now)
    relationships = _relationship_seeds(raw_event, payload, source_object)
    return NormalizationResult(
        raw_event_id=raw_event.id,
        normalized_version=NORMALIZED_VERSION,
        source_objects=[source_object],
        source_files=source_files,
        relationship_seeds=relationships,
    )


def _source_files(
    raw_event: RawEvent,
    payload: dict[str, Any],
    source_object: SourceObject,
    now: datetime,
) -> list[SourceFile]:
    if not bool(payload.get("creates_file", False)):
        return []
    fixture_id = _required_str(payload, "fixture_id")
    provider = _required_str(payload, "provider")
    content = _required_str(payload, "content")
    file_name_hash = _optional_str(payload, "file_name_hash")
    if file_name_hash is None:
        file_name_hash = sha256_digest(_required_str(payload, "file_name").encode())
    external_file_id = _optional_str(payload, "external_file_id") or fixture_id
    ocr_text_hash = sha256_digest(content.encode())
    return [
        SourceFile(
            id=stable_id("file", raw_event.workspace_id, provider, external_file_id),
            workspace_id=raw_event.workspace_id,
            source_object_id=source_object.id,
            source_connection_id=raw_event.source_connection_id,
            provider=provider,
            external_file_id=external_file_id,
            external_object_key=source_object.external_object_key,
            file_name_hash=file_name_hash,
            content_type=_optional_str(payload, "content_type")
            or "application/octet-stream",
            storage_ref=_optional_str(payload, "storage_ref")
            or f"fixture://files/{fixture_id}",
            content_hash=source_object.content_hash,
            ocr_text=content,
            ocr_text_hash=ocr_text_hash,
            metadata_json={
                "fixture_id": fixture_id,
                "ocr_fixture": True,
            },
            status=SourceObjectStatus.ACTIVE,
            trace_id=raw_event.trace_id,
            created_at=now,
            updated_at=now,
        )
    ]


def _relationship_seeds(
    raw_event: RawEvent, payload: dict[str, Any], source_object: SourceObject
) -> list[RelationshipSeed]:
    seeds = []
    for relation in payload.get("relationships", []):
        if not isinstance(relation, dict):
            raise FixtureNormalizationError("relationship entries must be objects")
        relationship_type = _required_str(relation, "type")
        target_id = _required_str(relation, "to_id")
        seed_id = stable_id(
            "rel",
            raw_event.workspace_id,
            relationship_type,
            source_object.id,
            target_id,
            NORMALIZED_VERSION,
        )
        seeds.append(
            RelationshipSeed(
                id=seed_id,
                workspace_id=raw_event.workspace_id,
                relationship_type=relationship_type,
                from_id=source_object.id,
                to_id=target_id,
                confidence=float(relation.get("confidence", 1.0)),
                raw_event_id=raw_event.id,
                normalized_version=NORMALIZED_VERSION,
                trace_id=raw_event.trace_id,
            )
        )
    return seeds


def _load_payload(payload_bytes: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError as error:
        raise FixtureNormalizationError("fixture payload is not valid JSON") from error
    if not isinstance(payload, dict):
        raise FixtureNormalizationError("fixture payload must be a JSON object")
    return payload


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise FixtureNormalizationError(f"fixture payload missing string field: {key}")
    return value


def _optional_str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise FixtureNormalizationError(
            f"fixture payload field must be a string: {key}"
        )
    return value


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise FixtureNormalizationError("occurred_at must be an ISO timestamp")
    return datetime.fromisoformat(value)
