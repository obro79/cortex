from __future__ import annotations

from uuid import uuid4

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider


def new_trace_id(prefix: str = "trace") -> str:
    return f"{prefix}_{uuid4().hex}"


def init_tracing(service_name: str = "cortex") -> None:
    provider = trace.get_tracer_provider()
    if provider.__class__.__name__ == "ProxyTracerProvider":
        trace.set_tracer_provider(TracerProvider())
    trace.get_tracer(service_name)
