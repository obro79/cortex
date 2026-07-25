from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cortex.contracts.pipeline_events import PipelineEventEnvelope


def valid_envelope_payload() -> dict:
    return {
        "event_id": "evt_raw_123",
        "event_type": "raw_event.persisted",
        "schema_version": "pipeline-event-v1",
        "occurred_at": "2026-05-06T18:12:00Z",
        "published_at": "2026-05-06T18:12:03Z",
        "workspace_id": "ws_1",
        "source_connection_id": "src_slack_arch",
        "provider": "slack",
        "partition_key": "ws_1:slack:T123:C456:thread:1715000000.000100",
        "external_object_key": "slack:T123:C456:thread:1715000000.000100",
        "subject": {"type": "raw_event", "id": "raw_123"},
        "causation": {
            "raw_event_id": "raw_123",
            "source_object_id": None,
            "source_chunk_id": None,
            "retrieval_request_id": None,
        },
        "versions": {
            "normalized_version": None,
            "chunking_version": None,
            "embedding_version": None,
            "index_version": None,
            "extractor_version": None,
            "gate_version": None,
        },
        "hashes": {
            "payload_hash": "sha256:rawpayload",
            "content_hash": None,
            "text_hash": None,
            "vector_hash": None,
        },
        "trace": {
            "trace_id": "trace_abc",
            "parent_event_id": None,
            "pipeline_run_id": "run_dev_1",
        },
        "producer": {"service": "ingestion-api", "instance_id": "api-1"},
        "retry": {"attempt": 0, "max_attempts": 5, "not_before": None},
        "payload": {"provider_event_type": "message.channels"},
    }


def test_pipeline_event_envelope_accepts_valid_example() -> None:
    envelope = PipelineEventEnvelope.model_validate(valid_envelope_payload())

    assert envelope.schema_version == "pipeline-event-v1"
    assert envelope.trace.trace_id == "trace_abc"
    assert envelope.payload == {"provider_event_type": "message.channels"}
    assert envelope.occurred_at == datetime(2026, 5, 6, 18, 12, tzinfo=UTC)


def test_pipeline_event_payload_defaults_to_empty_dict() -> None:
    payload = valid_envelope_payload()
    payload.pop("payload")

    assert PipelineEventEnvelope.model_validate(payload).payload == {}


@pytest.mark.parametrize(
    "missing_field",
    ["event_id", "event_type", "workspace_id", "partition_key", "subject", "trace"],
)
def test_pipeline_event_envelope_rejects_missing_required_fields(
    missing_field: str,
) -> None:
    payload = valid_envelope_payload()
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        PipelineEventEnvelope.model_validate(payload)


def test_pipeline_event_envelope_rejects_invalid_schema_version() -> None:
    payload = valid_envelope_payload()
    payload["schema_version"] = "pipeline-event-v2"

    with pytest.raises(ValidationError):
        PipelineEventEnvelope.model_validate(payload)


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "raw_payload",
        "source_text",
        "chunk_text",
        "ocr_text",
        "embedding",
        "vector",
        "oauth_token",
        "secret",
    ],
)
def test_pipeline_event_envelope_rejects_forbidden_payload_keys(
    forbidden_key: str,
) -> None:
    payload = valid_envelope_payload()
    payload["payload"] = {forbidden_key: "do-not-send"}

    with pytest.raises(ValidationError, match=forbidden_key):
        PipelineEventEnvelope.model_validate(payload)


def test_pipeline_event_envelope_rejects_nested_forbidden_payload_keys() -> None:
    payload = valid_envelope_payload()
    payload["payload"] = {"metadata": {"secret": "do-not-send"}}

    with pytest.raises(ValidationError, match="secret"):
        PipelineEventEnvelope.model_validate(payload)
