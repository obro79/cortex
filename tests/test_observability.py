from cortex.observability.logging import REDACTED, redact_mapping, setup_logging


def test_setup_logging_does_not_require_otel() -> None:
    setup_logging("INFO")


def test_redaction_removes_secret_content_keys() -> None:
    value = redact_mapping(
        {
            "oauth_token": "abc",
            "source_text": "content",
            "nested": {"vector": [1.0, 2.0]},
            "safe": "ok",
        }
    )
    assert value["oauth_token"] == REDACTED
    assert value["source_text"] == REDACTED
    assert value["nested"]["vector"] == REDACTED
    assert value["safe"] == "ok"
