from cortex.observability.logging import build_log_context
from cortex.observability.tracing import TraceContext
from cortex.security.redaction import REDACTED


def test_structured_log_context_keeps_correlation_and_redacts_sensitive_fields() -> (
    None
):
    context = build_log_context(
        "worker completed",
        trace=TraceContext(trace_id="trace_1", workspace_id="ws_1"),
        fields={
            "status": "ok",
            "source_text": "private source text",
            "private_url": "https://files.slack.com/private",
            "embedding": [1.0, 2.0],
            "query": "full user question must not be logged",
        },
    )

    assert context.message == "worker completed"
    assert context.fields["trace_id"] == "trace_1"
    assert context.fields["workspace_id"] == "ws_1"
    assert context.fields["status"] == "ok"
    assert context.fields["source_text"] == REDACTED
    assert context.fields["private_url"] == REDACTED
    assert context.fields["embedding"] == REDACTED
    assert context.fields["query"] == REDACTED
