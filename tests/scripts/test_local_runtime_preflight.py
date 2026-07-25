"""Regression coverage for the local dependency preflight."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "local_runtime_preflight.py"
SPEC = importlib.util.spec_from_file_location("local_runtime_preflight", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_frontend_preflight_rejects_empty_next_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "frontend" / "node_modules" / "next" / "package.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("", encoding="utf-8")

    failure = MODULE.check_frontend_runtime(tmp_path)

    assert failure is not None
    assert failure.name == "frontend runtime"
    assert "Next.js package.json is empty" in failure.detail


def test_repair_instructions_are_deterministic(tmp_path: Path) -> None:
    instructions = MODULE.repair_instructions(tmp_path)

    assert "uv sync --extra dev --reinstall" in instructions
    assert "(cd frontend && npm ci)" in instructions
    assert str(tmp_path) in instructions
