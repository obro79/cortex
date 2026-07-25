from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "stripe_activation_smoke", ROOT / "scripts" / "stripe_activation_smoke.py"
)
assert SPEC is not None
assert SPEC.loader is not None
stripe_activation_smoke = importlib.util.module_from_spec(SPEC)
sys.modules["stripe_activation_smoke"] = stripe_activation_smoke
SPEC.loader.exec_module(stripe_activation_smoke)

main = stripe_activation_smoke.main


def test_stripe_activation_static_smoke_passes() -> None:
    assert main(["--static"]) == 0


def test_stripe_activation_fake_gateway_smoke_dedupes_webhook(capsys) -> None:
    assert main(["--fake-gateway"]) == 0
    output = capsys.readouterr().out

    assert '"first_webhook_status": "processed"' in output
    assert '"webhook_duplicate": true' in output


def test_stripe_activation_list_mode_is_safe(capsys) -> None:
    assert main(["--list"]) == 0
    output = capsys.readouterr().out

    assert "static runbook" in output
    assert "fake gateway" in output
    assert "STRIPE_API_KEY" not in output
