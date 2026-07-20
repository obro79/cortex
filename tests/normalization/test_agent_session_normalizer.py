from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.connectors.agent_sessions import (
    EXPORT_MARKER,
    AgentCheckpointExport,
    content_hash_for_checkpoint,
)
from cortex.contracts.entities import RawEvent
from cortex.contracts.enums import RawEventStatus
from cortex.ingestion.payloads import canonical_json_bytes
from cortex.normalization.normalizers.agent_sessions import (
    normalize_agent_session_payload,
)
from cortex.normalization.normalizers.provider_payloads import (
    ProviderNormalizationError,
)
from cortex.normalization.registry import NormalizerRegistry


def _content() -> dict[str, object]:
    return {
        "checkpoint_id": "checkpoint_1",
        "provider": "claude_code",
        "task_state": "blocked",
        "task_summary": "Wait for the approved source export.",
        "decisions": [],
        "files": [
            {
                "path": ".env.production",
                "summary": "Configuration was reviewed.",
                "sensitive_path": False,
            }
        ],
        "commands": [{"summary": "pytest tests/connectors", "outcome": "passed"}],
        "tests": [{"summary": "focused tests", "outcome": "passed"}],
        "next_actions": ["Request a new explicit export."],
        "evidence_references": [{"label": "Issue", "reference": "COR-123"}],
        "visibility": "private",
    }


def _export() -> AgentCheckpointExport:
    content = _content()
    return AgentCheckpointExport(
        export_marker=EXPORT_MARKER,
        export_enabled=True,
        local_session_ref="caller-export-reference-0001",
        content_hash=content_hash_for_checkpoint(content),
        **content,
    )


def _raw_event(event_type: str = "agent_session.checkpoint.exported") -> RawEvent:
    now = datetime.now(UTC)
    return RawEvent(
        id="raw_checkpoint_1",
        workspace_id="ws_1",
        source_connection_id="src_agent_checkpoint",
        provider="agent_session",
        external_event_id="checkpoint_1",
        event_type=event_type,
        external_object_key="agent_session:checkpoint:checkpoint_1",
        idempotency_key="agent_session:1",
        payload_ref="memory://payload",
        payload_hash="sha256:payload",
        received_at=now,
        status=RawEventStatus.PUBLISHED,
        trace_id="trace_1",
        created_at=now,
        updated_at=now,
    )


def test_normalizer_emits_provenance_without_native_refs_or_sensitive_paths() -> None:
    result = normalize_agent_session_payload(
        _raw_event(), canonical_json_bytes(_export().to_payload())
    )

    source_object = result.source_objects[0]
    assert source_object.provider == "agent_session"
    assert source_object.object_type == "agent_checkpoint"
    assert (
        source_object.metadata_json["source_kind"] == "explicit_agent_checkpoint_export"
    )
    assert source_object.metadata_json["visibility"] == "private"
    assert source_object.metadata_json["transcript_capture"] == "not_supported"
    file_metadata = source_object.metadata_json["file_summaries"]
    assert file_metadata[0]["sensitive_path"] is True
    assert file_metadata[0]["path_hash"].startswith("sha256:")
    assert ".env.production" not in (source_object.content_text or "")
    assert "caller-export-reference" not in str(source_object.metadata_json)
    assert (
        source_object.metadata_json["local_session_ref_hash"]
        == _export().to_payload()["local_session_ref_hash"]
    )


def test_agent_checkpoint_content_is_chunked_with_safe_metadata() -> None:
    result = normalize_agent_session_payload(
        _raw_event(), canonical_json_bytes(_export().to_payload())
    )
    source_object = result.source_objects[0]

    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(source_object)[0]

    assert chunk.chunk_type == "agent_checkpoint_overview"
    assert "Task state: blocked" in chunk.text
    assert (
        chunk.metadata_json["local_session_ref_hash"]
        == _export().to_payload()["local_session_ref_hash"]
    )
    assert chunk.metadata_json["source_updated_at"] == (
        source_object.source_updated_at.isoformat()
    )
    assert "file_summaries" not in chunk.metadata_json
    assert "evidence_references" not in chunk.metadata_json


def test_normalizer_rejects_unmarked_disabled_or_transcript_payloads() -> None:
    payload = _export().to_payload()
    payload["export_enabled"] = False
    with pytest.raises(ProviderNormalizationError, match="explicitly enabled"):
        normalize_agent_session_payload(_raw_event(), canonical_json_bytes(payload))

    payload = _export().to_payload()
    payload["checkpoint"] = {**payload["checkpoint"], "full_transcript": "private"}
    with pytest.raises(ProviderNormalizationError, match="validation"):
        normalize_agent_session_payload(_raw_event(), canonical_json_bytes(payload))

    with pytest.raises(ProviderNormalizationError, match="unsupported"):
        normalize_agent_session_payload(
            _raw_event("agent_session.native.changed"), b"{}"
        )


def test_registry_resolves_agent_session_normalizer() -> None:
    assert (
        NormalizerRegistry().resolve(_raw_event()).__name__
        == "normalize_agent_session_payload"
    )
