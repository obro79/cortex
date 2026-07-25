from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "backup_restore_smoke", ROOT / "scripts" / "backup_restore_smoke.py"
)
assert SPEC is not None
assert SPEC.loader is not None
backup_restore_smoke = importlib.util.module_from_spec(SPEC)
sys.modules["backup_restore_smoke"] = backup_restore_smoke
SPEC.loader.exec_module(backup_restore_smoke)

main = backup_restore_smoke.main
smoke_commands = backup_restore_smoke.smoke_commands


def test_static_backup_restore_smoke_passes() -> None:
    assert main(["--static"]) == 0


def test_smoke_list_includes_static_and_full_commands(capsys) -> None:
    assert main(["--full", "--list"]) == 0
    output = capsys.readouterr().out

    assert "docs/runbooks/backup-restore.md" in output
    assert "alembic heads" in output
    assert "pg_dump" in output
    assert "pg_restore" in output


def test_backup_restore_runbook_documents_authority_boundaries() -> None:
    text = Path("docs/runbooks/backup-restore.md").read_text()

    assert "Postgres stores source records" in text
    assert "Object storage stores raw payloads" in text
    assert "Redis, Qdrant, and OpenSearch are not source-of-truth systems" in text
