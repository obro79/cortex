from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).parents[2] / "scripts" / "prepare_cortex_demo.py"


def _module() -> Any:
    spec = importlib.util.spec_from_file_location("prepare_cortex_demo", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pre_live_preparation_is_safe_and_exact() -> None:
    module = _module()
    report = module.preparation_report(
        phase="pre_live",
        settings=module.Settings(cortex_embedding_mode="real"),
    )

    assert report["ok"] is True
    assert report["mutation_performed"] is False
    assert report["workspace_id"] == "ws_demo_cor_123"
    assert report["selected_record_count"] == report["expected_corpus"]["pre_live"]
    assert report["expected_corpus"]["records"] == (
        report["expected_corpus"]["pre_live"] + 1
    )
    assert report["embedding_profile"] == {
        "mode": "real",
        "provider": "gemini",
        "model": "gemini-embedding-2",
        "version": "gemini2-1536-v1",
        "dimensions": 1536,
        "collection": (
            "cortex-local-gemini-embedding-2-gemini2-1536-v1-1536"
        ),
    }
    assert report["reset_scope"]["safe_to_apply_to_other_workspaces"] is False


def test_cli_emits_post_live_contract(capsys) -> None:
    module = _module()

    assert (
        module.main(
            ["--phase", "post_live", "--embedding-mode", "real", "--format", "json"]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)

    assert report["selected_record_count"] == report["expected_corpus"]["records"]
    assert report["mutation_performed"] is False


def test_cli_requires_explicit_disposable_runtime_for_mutations() -> None:
    module = _module()

    try:
        module.main(["--command", "seed"])
    except SystemExit as error:
        assert error.code == 2
    else:  # pragma: no cover - defensive assertion for argparse behavior
        raise AssertionError("seed without --in-memory should be rejected")


def test_cli_can_seed_only_the_disposable_runtime(capsys) -> None:
    module = _module()

    assert (
        module.main(["--command", "seed", "--in-memory", "--phase", "pre_live"])
        == 0
    )
    report = json.loads(capsys.readouterr().out)

    assert report["mutation_performed"] is True
    assert report["mutation_target"] == "in_memory_demo_runtime"
    assert report["created_count"] == report["selected_record_count"]
