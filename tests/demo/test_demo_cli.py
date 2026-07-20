from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Protocol, cast

from pytest import CaptureFixture

from cortex.demo import DemoEvidenceControlPlane


class DemoCli(Protocol):
    def render_human(self, report: object) -> str: ...

    async def main(self, argv: list[str] | None = None) -> int: ...


def _load_cli_module() -> DemoCli:
    path = Path("scripts/demo_evidence_report.py")
    spec = importlib.util.spec_from_file_location("demo_evidence_report", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(DemoCli, module)


async def test_human_renderer_is_fixture_safe() -> None:
    cli = _load_cli_module()
    rendered = cli.render_human(await DemoEvidenceControlPlane().build_report())

    assert "Synthetic deterministic fixtures only" in rendered
    assert "handoff=blocked_pending_human_review" in rendered
    assert "https://" not in rendered
    assert "Postgres is the approved" not in rendered


async def test_json_output_is_parseable_and_explicitly_not_live(
    capsys: CaptureFixture[str],
) -> None:
    cli = _load_cli_module()
    assert await cli.main(["--format", "json"]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert report["live_data"] is False
    assert report["decision"]["gate_status"] == "block"
