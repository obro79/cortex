from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from cortex.security.redaction import is_sensitive_key

MetricKind = Literal["counter", "histogram", "gauge"]

SAFE_LABEL_KEYS = frozenset(
    {
        "provider",
        "stage",
        "status",
        "worker",
        "topic",
        "source_type",
        "operation",
        "severity",
    }
)

METRIC_PREFIX = "cortex"


@dataclass(frozen=True)
class MetricPoint:
    name: str
    kind: MetricKind
    value: float
    labels: dict[str, str]


class UnsafeMetricLabelError(ValueError):
    pass


class InMemoryMetricSink:
    def __init__(self) -> None:
        self._points: list[MetricPoint] = []

    def emit(
        self,
        *,
        name: str,
        kind: MetricKind,
        value: float,
        labels: Mapping[str, str] | None = None,
    ) -> MetricPoint:
        point = MetricPoint(
            name=safe_metric_name(name),
            kind=kind,
            value=value,
            labels=safe_metric_labels(labels or {}),
        )
        self._points.append(point)
        return point

    def list_points(self) -> list[MetricPoint]:
        return list(self._points)


def safe_metric_name(name: str) -> str:
    stripped = name.strip().lower().replace(".", "_").replace("-", "_")
    if not stripped:
        msg = "metric name must be non-empty"
        raise ValueError(msg)
    if not stripped.startswith(f"{METRIC_PREFIX}_"):
        stripped = f"{METRIC_PREFIX}_{stripped}"
    return stripped


def safe_metric_labels(labels: Mapping[str, str]) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, value in labels.items():
        if key not in SAFE_LABEL_KEYS or is_sensitive_key(key):
            msg = f"unsafe metric label: {key}"
            raise UnsafeMetricLabelError(msg)
        if _looks_sensitive_value(value) or _looks_high_cardinality(value):
            msg = f"unsafe metric label value for: {key}"
            raise UnsafeMetricLabelError(msg)
        safe[key] = value
    return safe


def _looks_high_cardinality(value: str) -> bool:
    return (
        "://" in value
        or "/" in value
        or len(value) > 64
        or value.startswith(("src_", "raw_", "so_"))
    )


def _looks_sensitive_value(value: str) -> bool:
    lowered = value.lower()
    return (
        lowered.startswith(("xox", "ghp_", "github_pat_"))
        or "bearer " in lowered
        or "secret" in lowered
        or "private" in lowered
    )
