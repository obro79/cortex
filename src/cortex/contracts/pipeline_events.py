"""Pipeline event envelope contracts for Kafka-carried work notifications."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cortex.contracts.ids import JsonObject

PIPELINE_EVENT_SCHEMA_VERSION: Literal["pipeline-event-v1"] = "pipeline-event-v1"

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "raw_payload",
        "source_text",
        "chunk_text",
        "ocr_text",
        "embedding",
        "vector",
        "oauth_token",
        "secret",
    }
)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class PipelineSubject(ContractModel):
    type: str
    id: str


class PipelineCausation(ContractModel):
    raw_event_id: str | None = None
    source_object_id: str | None = None
    source_chunk_id: str | None = None
    retrieval_request_id: str | None = None


class PipelineVersions(ContractModel):
    normalized_version: str | None = None
    chunking_version: str | None = None
    embedding_version: str | None = None
    index_version: str | None = None
    extractor_version: str | None = None
    gate_version: str | None = None


class PipelineHashes(ContractModel):
    payload_hash: str | None = None
    content_hash: str | None = None
    text_hash: str | None = None
    vector_hash: str | None = None


class PipelineTrace(ContractModel):
    trace_id: str
    parent_event_id: str | None = None
    pipeline_run_id: str | None = None


class PipelineProducer(ContractModel):
    service: str
    instance_id: str | None = None


class PipelineRetry(ContractModel):
    attempt: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=5, ge=0)
    not_before: datetime | None = None


class PipelineEventEnvelope(ContractModel):
    event_id: str
    event_type: str
    schema_version: Literal["pipeline-event-v1"] = PIPELINE_EVENT_SCHEMA_VERSION
    occurred_at: datetime | None = None
    published_at: datetime | None = None
    workspace_id: str
    source_connection_id: str | None = None
    provider: str | None = None
    partition_key: str
    external_object_key: str | None = None
    subject: PipelineSubject
    causation: PipelineCausation = Field(default_factory=PipelineCausation)
    versions: PipelineVersions = Field(default_factory=PipelineVersions)
    hashes: PipelineHashes = Field(default_factory=PipelineHashes)
    trace: PipelineTrace
    producer: PipelineProducer | None = None
    retry: PipelineRetry = Field(default_factory=PipelineRetry)
    payload: JsonObject = Field(default_factory=dict)

    @field_validator("event_id", "event_type", "workspace_id", "partition_key")
    @classmethod
    def non_empty_required_string(cls, value: str) -> str:
        if not value:
            msg = "field must be a non-empty string"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def payload_must_not_carry_content_or_secrets(self) -> "PipelineEventEnvelope":
        forbidden = sorted(FORBIDDEN_PAYLOAD_KEYS.intersection(self.payload.keys()))
        if forbidden:
            found = ", ".join(forbidden)
            msg = f"payload contains forbidden content-bearing keys: {found}"
            raise ValueError(msg)
        self._reject_nested_forbidden_payload_keys(self.payload)
        return self

    @classmethod
    def _reject_nested_forbidden_payload_keys(cls, value: Any) -> None:
        if isinstance(value, dict):
            forbidden = sorted(FORBIDDEN_PAYLOAD_KEYS.intersection(value.keys()))
            if forbidden:
                found = ", ".join(forbidden)
                msg = f"payload contains forbidden content-bearing keys: {found}"
                raise ValueError(msg)
            for child in value.values():
                cls._reject_nested_forbidden_payload_keys(child)
        elif isinstance(value, list):
            for child in value:
                cls._reject_nested_forbidden_payload_keys(child)
