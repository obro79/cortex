from __future__ import annotations

import runpy
from pathlib import Path


def _smoke_module() -> dict[str, object]:
    return runpy.run_path(
        Path(__file__).parents[3] / "scripts" / "kafka_slack_e2e_smoke.py"
    )


async def test_fixture_readiness_proves_selected_webhook_and_backfill_offline() -> None:
    module = _smoke_module()
    run_fixture_proof = module["run_fixture_proof"]

    result = await run_fixture_proof()

    assert result == {
        "ok": True,
        "mode": "fixture",
        "network_access": False,
        "live_slack_ingestion": False,
        "selected_source_id": result["selected_source_id"],
        "webhook_status": "persisted",
        "backfill_status": "completed",
        "raw_events": 2,
    }


def test_preflight_reports_missing_live_prerequisites_without_contacting_slack(
    monkeypatch,
) -> None:
    module = _smoke_module()
    for name in module["live_prerequisites"]():
        monkeypatch.delenv(name, raising=False)

    result = module["preflight"]()

    assert result["ok"] is False
    assert result["network_access"] is False
    assert result["live_slack_ingestion"] is False
    assert result["live_prerequisites"] == {
        "SLACK_CLIENT_ID": False,
        "SLACK_CLIENT_SECRET": False,
        "SLACK_SIGNING_SECRET": False,
        "SLACK_REDIRECT_URI": False,
    }
