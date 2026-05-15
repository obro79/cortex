from pathlib import Path


def test_provider_acl_refresh_runbook_requires_token_env_not_inline_tokens() -> None:
    text = Path("docs/runbooks/provider-acl-refresh.md").read_text()
    normalized = " ".join(text.split())

    assert "CORTEX_PROVIDER_ACL_REFRESH_TARGETS_JSON" in text
    assert "token_env" in text
    assert "provider tokens directly in JSON" in normalized
    assert "cortex-worker --role provider-acl" in text
    assert "provider-acl-refresh" in text
