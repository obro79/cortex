from __future__ import annotations

import runpy
from pathlib import Path


def _module() -> dict[str, object]:
    return runpy.run_path(
        Path(__file__).parents[2] / "scripts" / "live_sources_preflight.py"
    )


def test_preflight_is_credential_safe_and_requires_both_live_sources(
    monkeypatch,
) -> None:
    module = _module()
    for name in (
        "SLACK_CLIENT_ID",
        "SLACK_CLIENT_SECRET",
        "SLACK_SIGNING_SECRET",
        "SLACK_REDIRECT_URI",
        "GITHUB_WEBHOOK_SECRET",
        "GITHUB_INSTALLATION_TOKEN",
        "GITHUB_APP_ID",
        "GITHUB_PRIVATE_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    result = module["preflight"]()

    assert result["ok"] is False
    assert result["network_access"] is False
    assert result["provider_calls"] is False
    assert "GITHUB_INSTALLATION_TOKEN" in result["providers"]["github"]["environment"]


def test_preflight_accepts_github_app_credentials_without_exposing_values(
    monkeypatch,
) -> None:
    module = _module()
    values = {
        "SLACK_CLIENT_ID": "id",
        "SLACK_CLIENT_SECRET": "secret",
        "SLACK_SIGNING_SECRET": "signing",
        "SLACK_REDIRECT_URI": "http://localhost/callback",
        "GITHUB_WEBHOOK_SECRET": "webhook",
        "GITHUB_APP_ID": "123",
        "GITHUB_PRIVATE_KEY": "private-key-material",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    result = module["preflight"]()

    assert result["ok"] is True
    assert "private-key-material" not in str(result)
    assert (
        result["providers"]["github"]["auth"] == "installation_token_or_app_credentials"
    )
