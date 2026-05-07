from cortex.dev.pipeline import STAGES
from cortex.dev.workbench import DevWorkbenchService


async def test_pipeline_run_records_ordered_traceable_stages() -> None:
    service = DevWorkbenchService()
    service.seed()
    run = await service.run_pipeline()

    assert run["run_id"] == "run-cor-123-001"
    assert [stage["stage"] for stage in run["stages"]] == list(STAGES)
    assert all(stage["status"] == "completed" for stage in run["stages"])
    assert all(stage["trace_id"] == "trace-run-cor-123-001" for stage in run["stages"])
    assert all(
        stage["event_id"].startswith("evt-run-cor-123-001") for stage in run["stages"]
    )
    assert len(service.event_bus.list_events()) == len(STAGES)
    assert run["artifact_ids"]["evidence_pack"] == "ep-cor-123"


async def test_repeated_runs_are_deterministic_for_artifacts() -> None:
    service = DevWorkbenchService()
    service.seed()
    first = await service.run_pipeline()
    second = await service.run_pipeline()

    assert first["artifact_ids"] == second["artifact_ids"]
    assert second["run_id"] == "run-cor-123-002"
