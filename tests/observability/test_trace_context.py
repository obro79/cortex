from cortex.observability.tracing import (
    TraceContext,
    ensure_trace_context,
    init_tracing,
    reset_trace_context,
    safe_correlation_fields,
    set_trace_context,
)


def test_tracing_defaults_to_disabled_without_exporter() -> None:
    state = init_tracing(service_name="cortex-test", enabled=False)

    assert state.service_name == "cortex-test"
    assert state.enabled is False


def test_trace_context_carries_required_correlation_fields() -> None:
    context = TraceContext(
        trace_id="trace_1",
        workspace_id="ws_1",
        source_connection_id="src_1",
        pipeline_run_id="run_1",
        kafka_topic="raw-events",
        worker_name="normalization-worker",
        retrieval_request_id="ret_1",
        evidence_pack_id="ep_1",
    )

    assert context.as_log_fields() == {
        "trace_id": "trace_1",
        "workspace_id": "ws_1",
        "source_connection_id": "src_1",
        "pipeline_run_id": "run_1",
        "kafka_topic": "raw-events",
        "worker_name": "normalization-worker",
        "retrieval_request_id": "ret_1",
        "evidence_pack_id": "ep_1",
    }


def test_ensure_trace_context_extends_current_context() -> None:
    token = set_trace_context(TraceContext(trace_id="trace_1", workspace_id="ws_1"))

    try:
        context = ensure_trace_context(worker_name="embedding-worker")
    finally:
        reset_trace_context(token)

    assert context.trace_id == "trace_1"
    assert context.workspace_id == "ws_1"
    assert context.worker_name == "embedding-worker"


def test_ensure_trace_context_keeps_fields_when_creating_context() -> None:
    context = ensure_trace_context(
        trace_id="trace_2",
        workspace_id="ws_1",
        source_connection_id="src_1",
    )

    assert context.trace_id == "trace_2"
    assert context.workspace_id == "ws_1"
    assert context.source_connection_id == "src_1"


def test_reset_trace_context_restores_previous_context() -> None:
    token = set_trace_context(TraceContext(trace_id="trace_3"))

    reset_trace_context(token)

    context = ensure_trace_context(trace_id="trace_4")
    assert context.trace_id == "trace_4"


def test_safe_correlation_fields_drops_non_correlation_data() -> None:
    fields = safe_correlation_fields(
        {
            "trace_id": "trace_1",
            "workspace_id": "ws_1",
            "source_text": "do not log",
            "access_token": "secret",
        }
    )

    assert fields == {"trace_id": "trace_1", "workspace_id": "ws_1"}
