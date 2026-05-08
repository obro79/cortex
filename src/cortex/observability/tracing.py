from __future__ import annotations

from collections.abc import Mapping
from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import uuid4

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from cortex.security.redaction import redact_mapping

REQUIRED_CORRELATION_FIELDS = frozenset(
    {
        "trace_id",
        "workspace_id",
        "source_connection_id",
        "pipeline_run_id",
        "kafka_topic",
        "worker_name",
        "retrieval_request_id",
        "evidence_pack_id",
    }
)

_current_trace_context: ContextVar[TraceContext | None] = ContextVar(
    "cortex_trace_context", default=None
)


@dataclass(frozen=True)
class TracingState:
    service_name: str
    enabled: bool


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    workspace_id: str | None = None
    source_connection_id: str | None = None
    pipeline_run_id: str | None = None
    kafka_topic: str | None = None
    worker_name: str | None = None
    retrieval_request_id: str | None = None
    evidence_pack_id: str | None = None

    def as_log_fields(self) -> dict[str, str]:
        return {
            key: value
            for key, value in {
                "trace_id": self.trace_id,
                "workspace_id": self.workspace_id,
                "source_connection_id": self.source_connection_id,
                "pipeline_run_id": self.pipeline_run_id,
                "kafka_topic": self.kafka_topic,
                "worker_name": self.worker_name,
                "retrieval_request_id": self.retrieval_request_id,
                "evidence_pack_id": self.evidence_pack_id,
            }.items()
            if value
        }


def new_trace_id(prefix: str = "trace") -> str:
    return f"{prefix}_{uuid4().hex}"


def init_tracing(
    service_name: str = "cortex", *, enabled: bool = False
) -> TracingState:
    if not enabled:
        return TracingState(service_name=service_name, enabled=False)
    provider = trace.get_tracer_provider()
    if provider.__class__.__name__ == "ProxyTracerProvider":
        resource = Resource.create({"service.name": service_name})
        trace.set_tracer_provider(TracerProvider(resource=resource))
    trace.get_tracer(service_name)
    return TracingState(service_name=service_name, enabled=True)


def set_trace_context(context: TraceContext) -> Token[TraceContext | None]:
    return _current_trace_context.set(context)


def reset_trace_context(token: Token[TraceContext | None]) -> None:
    _current_trace_context.reset(token)


def get_trace_context() -> TraceContext | None:
    return _current_trace_context.get()


def ensure_trace_context(
    context: TraceContext | None = None, **fields: str | None
) -> TraceContext:
    current = context or get_trace_context()
    update = {
        key: value
        for key, value in fields.items()
        if key in REQUIRED_CORRELATION_FIELDS and value
    }
    if current is None:
        trace_id = update.pop("trace_id", None) or new_trace_id()
        return TraceContext(trace_id=trace_id, **update)
    if not update:
        return current
    return current.__class__(**{**current.as_log_fields(), **update})


def safe_correlation_fields(fields: Mapping[str, object]) -> dict[str, object]:
    allowed = {
        key: value
        for key, value in fields.items()
        if key in REQUIRED_CORRELATION_FIELDS and value is not None
    }
    return redact_mapping(allowed)
