from __future__ import annotations

from pathlib import Path


def test_ingress_contract_documents_managed_proxy_assumptions() -> None:
    text = Path("docs/deployment/ingress-contract.md").read_text()

    assert "managed ingress or reverse proxy" in text
    assert "Terminate TLS" in text
    assert "/health/live" in text
    assert "/health/ready" in text
    assert "Rate-limit middleware exempts health paths" in text
    assert "must not include OAuth tokens" in text


def test_phase_13_validation_evidence_lists_required_checks() -> None:
    text = Path(
        "docs/phases/phase-13-layer-later-platform/run-logs/"
        "2026-05-08-phase-13-validation.md"
    ).read_text()

    assert "uv run ruff format --check ." in text
    assert "uv run pytest" in text
    assert "backup_restore_smoke.py --static" in text
    assert "derived_index_rebuild_smoke.py --static" in text
    assert "Redis remains optional" in text
