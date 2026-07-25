from __future__ import annotations

import json
import runpy
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts" / "live_context_preflight.py"
FIXTURE = (
    Path(__file__).parents[2]
    / "docs"
    / "hackathon"
    / "live-context-run-report.example.json"
)


def _module() -> dict[str, object]:
    return runpy.run_path(SCRIPT)


def _clear_environment(monkeypatch) -> None:
    for name in (
        "DATABASE_URL",
        "KAFKA_BOOTSTRAP_SERVERS",
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "GEMINI_API_KEY",
        "CORTEX_SECRET_ENCRYPTION_KEY",
        "SLACK_CLIENT_ID",
        "SLACK_CLIENT_SECRET",
        "SLACK_SIGNING_SECRET",
        "SLACK_REDIRECT_URI",
        "CORTEX_EVENT_BUS",
        "CORTEX_STATE_BACKEND",
        "CORTEX_EMBEDDING_MODE",
        "CORTEX_SLACK_CONNECTOR_ENABLED",
        "QDRANT_COLLECTION_PREFIX",
    ):
        monkeypatch.delenv(name, raising=False)


def test_preflight_reports_missing_configuration_without_secret_values(
    monkeypatch,
) -> None:
    _clear_environment(monkeypatch)
    monkeypatch.setenv("SLACK_CLIENT_SECRET", "never-print-this-secret")
    result = _module()["preflight"]()

    assert result["ok"] is False
    assert result["configuration_ready"] is False
    assert result["network_access"] is False
    assert result["provider_calls"] is False
    assert result["secret_values_emitted"] is False
    assert result["environment"]["SLACK_CLIENT_SECRET"] is True
    assert "never-print-this-secret" not in str(result)
    assert result["next_action"].startswith("Configure the missing")


def test_preflight_accepts_complete_hosted_contract_without_contacting_services(
    monkeypatch,
) -> None:
    _clear_environment(monkeypatch)
    values = {
        "DATABASE_URL": "postgresql+asyncpg://ignored",
        "KAFKA_BOOTSTRAP_SERVERS": "broker:9092",
        "QDRANT_URL": "https://qdrant.example.test",
        "QDRANT_API_KEY": "qdrant-secret",
        "GEMINI_API_KEY": "gemini-secret",
        "CORTEX_SECRET_ENCRYPTION_KEY": "encryption-secret",
        "SLACK_CLIENT_ID": "client-id",
        "SLACK_CLIENT_SECRET": "client-secret",
        "SLACK_SIGNING_SECRET": "signing-secret",
        "SLACK_REDIRECT_URI": "http://localhost/callback",
        "CORTEX_EVENT_BUS": "kafka",
        "CORTEX_STATE_BACKEND": "sql",
        "CORTEX_EMBEDDING_MODE": "real",
        "CORTEX_SLACK_CONNECTOR_ENABLED": "true",
        "QDRANT_COLLECTION_PREFIX": "cortex",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    module = _module()
    monkeypatch.setattr(module["shutil"], "which", lambda _: None)

    result = module["preflight"]()

    assert result["configuration_ready"] is True
    assert result["qdrant_contract"]["hosted"] is True
    assert result["qdrant_contract"]["api_key_present"] is True
    assert result["local_dependencies"]["status"] == "docker_unavailable"
    for secret in (
        "qdrant-secret",
        "gemini-secret",
        "encryption-secret",
        "client-secret",
    ):
        assert secret not in str(result)


def test_live_run_report_fixture_matches_redacted_json_contract() -> None:
    module = _module()
    report = json.loads(FIXTURE.read_text())

    assert module["validate_live_run_report"](report) == []

    report["query"] = "must not be accepted"
    assert "unexpected field: query" in module["validate_live_run_report"](report)
