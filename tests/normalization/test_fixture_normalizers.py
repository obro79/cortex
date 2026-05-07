from datetime import UTC, datetime

import pytest

from cortex.contracts.entities import RawEvent
from cortex.contracts.enums import RawEventStatus, SourceObjectStatus
from cortex.ingestion.payloads import canonical_json_bytes
from cortex.normalization.normalizers.fixtures import (
    FixtureNormalizationError,
    normalize_fixture_payload,
)


def raw_event(provider: str = "slack") -> RawEvent:
    now = datetime.now(UTC)
    return RawEvent(
        id="raw_1",
        workspace_id="ws_1",
        source_connection_id="src_1",
        provider=provider,
        external_event_id="evt_1",
        event_type=f"{provider}.fixture",
        external_object_key=f"{provider}:fixture_1",
        idempotency_key="fixture:1",
        payload_ref="memory://payloads/1",
        payload_hash="sha256:payload",
        received_at=now,
        status=RawEventStatus.PUBLISHED,
        trace_id="trace_1",
        created_at=now,
        updated_at=now,
    )


def fixture_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "fixture_id": "slack-file-session-flow-diagram",
        "provider": "slack",
        "object_type": "diagram_file",
        "title": "Session flow diagram OCR",
        "canonical_url": "https://fixtures.local/slack/session-flow-diagram",
        "content": "OCR: browser writes session token.",
        "source_kind": "diagram_ocr",
        "creates_file": True,
        "file_name_hash": "sha256:file-name",
        "content_type": "image/png",
        "occurred_at": "2026-05-06T18:12:00+00:00",
        "relationships": [
            {
                "type": "mentions_issue",
                "to_id": "so-linear-issue-COR-123",
                "confidence": 0.9,
            }
        ],
    }
    payload.update(updates)
    return payload


def test_fixture_normalizer_creates_source_object_file_and_relationship_seed() -> None:
    result = normalize_fixture_payload(
        raw_event(),
        canonical_json_bytes(fixture_payload()),
    )

    source_object = result.source_objects[0]
    source_file = result.source_files[0]
    relationship = result.relationship_seeds[0]

    assert result.normalized_version == "fixture-normalizer-v1"
    assert source_object.id.startswith("so_")
    assert source_object.object_type == "diagram_file"
    assert source_object.content_hash is not None
    assert source_object.metadata_json == {
        "fixture_id": "slack-file-session-flow-diagram",
        "source_kind": "diagram_ocr",
        "is_stale": False,
    }
    assert source_file.id.startswith("file_")
    assert source_file.source_object_id == source_object.id
    assert source_file.ocr_text == "OCR: browser writes session token."
    assert source_file.ocr_text_hash == source_object.content_hash
    assert relationship.from_id == source_object.id
    assert relationship.to_id == "so-linear-issue-COR-123"


def test_fixture_normalizer_marks_stale_records_without_content_in_metadata() -> None:
    result = normalize_fixture_payload(
        raw_event("repo_docs"),
        canonical_json_bytes(
            fixture_payload(
                provider="repo_docs",
                object_type="repo_doc_section",
                creates_file=False,
                is_stale=True,
            )
        ),
    )

    source_object = result.source_objects[0]

    assert source_object.status == SourceObjectStatus.STALE
    assert "content" not in source_object.metadata_json
    assert result.source_files == []


def test_invalid_fixture_payload_shape_is_structured_error() -> None:
    with pytest.raises(FixtureNormalizationError, match="missing string field"):
        normalize_fixture_payload(
            raw_event(), canonical_json_bytes({"provider": "slack"})
        )
