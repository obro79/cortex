from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cortex.security.redaction import REDACTED, is_sensitive_key, redact_mapping

from .tracing import TraceContext, safe_correlation_fields


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@dataclass(frozen=True)
class StructuredLogContext:
    message: str
    fields: dict[str, object]


def build_log_context(
    message: str,
    *,
    trace: TraceContext | None = None,
    fields: Mapping[str, Any] | None = None,
) -> StructuredLogContext:
    safe_fields: dict[str, object] = {}
    if trace is not None:
        safe_fields.update(trace.as_log_fields())
    if fields is not None:
        safe_fields.update(redact_mapping(fields))
    correlation = safe_correlation_fields(safe_fields)
    extras = {
        key: value for key, value in safe_fields.items() if key not in correlation
    }
    return StructuredLogContext(
        message=message,
        fields=correlation | extras,
    )


__all__ = [
    "REDACTED",
    "StructuredLogContext",
    "build_log_context",
    "is_sensitive_key",
    "redact_mapping",
    "setup_logging",
]
