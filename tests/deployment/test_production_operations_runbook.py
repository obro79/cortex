from pathlib import Path

RUNBOOK = Path("docs/runbooks/production-operations.md")


def test_production_operations_runbook_covers_required_sections() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    for heading in [
        "## Topology",
        "## CI/CD",
        "## Migration Strategy",
        "## Alerts",
        "## Support Diagnostics",
        "## Load And Cost Tests",
        "## Rollback",
        "## Drill Evidence",
    ]:
        assert heading in text


def test_support_diagnostics_boundary_excludes_raw_content_and_secrets() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "provider tokens" in text
    assert "session tokens" in text
    assert "raw message or document content" in text
    assert "private file URLs" in text
    assert "trace ID" in text


def test_migration_strategy_requires_explicit_migrate_job() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "Migrations are never run implicitly" in text
    assert "Run `migrate` once" in text
    assert "Data-destructive migrations require a restore point" in text
