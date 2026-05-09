from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "derived_index_rebuild_smoke", ROOT / "scripts" / "derived_index_rebuild_smoke.py"
)
assert SPEC is not None
assert SPEC.loader is not None
derived_index_rebuild_smoke = importlib.util.module_from_spec(SPEC)
sys.modules["derived_index_rebuild_smoke"] = derived_index_rebuild_smoke
SPEC.loader.exec_module(derived_index_rebuild_smoke)

main = derived_index_rebuild_smoke.main


def test_static_derived_index_rebuild_smoke_passes() -> None:
    assert main(["--static"]) == 0


def test_derived_index_rebuild_list_includes_parity_checks(capsys) -> None:
    assert main(["--full", "--list"]) == 0
    output = capsys.readouterr().out

    assert "docs/runbooks/derived-index-rebuild.md" in output
    assert "tests/dev/test_evals.py" in output
    assert "tests/retrieval/test_retrieval_service.py" in output


def test_derived_index_runbook_marks_indexes_rebuildable() -> None:
    text = Path("docs/runbooks/derived-index-rebuild.md").read_text()

    assert "Qdrant and OpenSearch are derived indexes" in text
    assert "Postgres source objects" in text
    assert "not private snippets or raw source content" in text
