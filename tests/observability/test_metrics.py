import pytest

from cortex.observability.metrics import (
    InMemoryMetricSink,
    UnsafeMetricLabelError,
    safe_metric_labels,
    safe_metric_name,
)


def test_metric_names_are_normalized_under_cortex_prefix() -> None:
    assert safe_metric_name("retrieval.latency-ms") == "cortex_retrieval_latency_ms"
    assert safe_metric_name("cortex_worker_jobs") == "cortex_worker_jobs"


def test_metric_sink_accepts_safe_low_cardinality_labels() -> None:
    sink = InMemoryMetricSink()

    point = sink.emit(
        name="worker.jobs",
        kind="counter",
        value=1,
        labels={
            "provider": "slack",
            "stage": "normalization",
            "status": "completed",
            "worker": "normalizer",
            "topic": "raw-events",
        },
    )

    assert point.name == "cortex_worker_jobs"
    assert point.labels["provider"] == "slack"
    assert sink.list_points() == [point]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("workspace_id", "ws_1"),
        ("url", "https://private.example"),
        ("provider", "https://private.example"),
        ("source_type", "src_hidden_source"),
    ],
)
def test_metric_labels_reject_unsafe_or_high_cardinality_values(
    key: str, value: str
) -> None:
    with pytest.raises(UnsafeMetricLabelError):
        safe_metric_labels({key: value})
