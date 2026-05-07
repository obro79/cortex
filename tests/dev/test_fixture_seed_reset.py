from cortex.dev.workbench import DevWorkbenchService


def test_seed_uses_stable_ids_and_is_idempotent() -> None:
    service = DevWorkbenchService()
    first = service.seed()
    second = service.seed()

    assert first["fixture_ids"] == second["fixture_ids"]
    assert "slack-thread-sessions-postgres" in first["fixture_ids"]
    assert "linear-issue-COR-123" in first["fixture_ids"]
    assert first["counts"] == second["counts"]
    assert first["counts"]["raw_events"] == 6
    assert first["counts"]["source_files"] == 1


def test_reset_clears_dev_state_only() -> None:
    service = DevWorkbenchService()
    service.seed()
    reset = service.reset()

    assert reset["status"] == "reset"
    assert reset["state"]["seeded"] is False
    assert reset["state"]["fixture_counts"]["source_objects"] == 0
