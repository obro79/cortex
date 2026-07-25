from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "backend_ops_launch_gate", ROOT / "scripts" / "backend_ops_launch_gate.py"
)
assert SPEC is not None
assert SPEC.loader is not None
backend_ops_launch_gate = importlib.util.module_from_spec(SPEC)
sys.modules["backend_ops_launch_gate"] = backend_ops_launch_gate
SPEC.loader.exec_module(backend_ops_launch_gate)

gate_commands = backend_ops_launch_gate.gate_commands
main = backend_ops_launch_gate.main
write_evidence = backend_ops_launch_gate.write_evidence


def test_backend_ops_launch_gate_lists_no_secret_commands(capsys) -> None:
    assert main(["--list"]) == 0
    output = capsys.readouterr().out

    assert "uv run ruff check ." in output
    assert "docker compose --profile provider-acl config" in output
    assert "scripts/stripe_activation_smoke.py --static --fake-gateway" in output
    assert "STRIPE_API_KEY" not in output


def test_backend_ops_launch_gate_contains_expected_backend_checks() -> None:
    names = [command.name for command in gate_commands()]

    assert "focused backend tests" in names
    assert "compose provider-acl config" in names
    assert "alembic upgrade sql" in names
    assert "stripe activation static smoke" in names


def test_backend_ops_launch_gate_writes_local_evidence(tmp_path) -> None:
    evidence = tmp_path / "evidence.md"
    command = gate_commands()[0]

    write_evidence(
        path=evidence,
        results=[(command, "All checks passed")],
        status="passed",
    )

    text = evidence.read_text()
    assert "Environment: local" in text
    assert "not staging evidence" in text
    assert "Residual Risk" in text
    assert "Live Stripe checkout" in text
