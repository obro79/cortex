import pytest

from cortex.security.redaction import REDACTED, assert_payload_safe, redact_mapping


def test_redaction_removes_tokens_text_urls_and_nested_private_file_data() -> None:
    value = {
        "ok": True,
        "access_token": "xoxb-secret",
        "message_text": "private slack text",
        "nested": {
            "url_private_download": "https://files.slack.com/private",
            "count": 1,
        },
    }

    redacted = redact_mapping(value)

    assert redacted == {
        "ok": True,
        "access_token": REDACTED,
        "message_text": REDACTED,
        "nested": {
            "url_private_download": REDACTED,
            "count": 1,
        },
    }


def test_payload_safety_rejects_nested_content_and_secret_keys() -> None:
    with pytest.raises(ValueError, match="message_text"):
        assert_payload_safe({"metadata": {"message_text": "do not emit"}})
