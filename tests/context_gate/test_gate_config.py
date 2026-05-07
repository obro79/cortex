from pathlib import Path

import pytest
from pydantic import ValidationError

from cortex.chunking.config import load_retrieval_config


def test_gate_config_defaults_match_phase_6() -> None:
    config = load_retrieval_config().context_gate

    assert config.version == "gate-v1"
    assert config.high_confidence_conflict_threshold == 0.8
    assert config.stale_context_days == 90
    assert config.min_required_sources_for_high_risk_tasks == 2
    assert config.block_on_permission_uncertainty is True


def test_gate_config_rejects_invalid_values(tmp_path: Path) -> None:
    path = tmp_path / "retrieval.yaml"
    path.write_text(
        Path("config/retrieval-v1.yaml")
        .read_text()
        .replace("version: gate-v1", "version: gate")
        .replace("stale_context_days: 90", "stale_context_days: -1")
    )

    with pytest.raises(ValidationError):
        load_retrieval_config(path)
