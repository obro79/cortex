import pytest
import typer

from cortex.config import Settings
from cortex.workers.heartbeat import InMemoryWorkerHeartbeatRepository
from cortex.workers.main import run_worker


async def test_noop_worker_records_ready_heartbeat() -> None:
    heartbeats = InMemoryWorkerHeartbeatRepository()

    result = await run_worker(
        "noop",
        settings=Settings(),
        heartbeat_repository=heartbeats,
        instance_id="worker_1",
    )

    assert result == 0
    summaries = [heartbeat.safe_summary() for heartbeat in heartbeats.list_all()]
    assert len(summaries) == 1
    assert summaries[0]["role"] == "noop"
    assert summaries[0]["instance_id"] == "worker_1"
    assert summaries[0]["status"] == "ready"
    assert "last_heartbeat_at" in summaries[0]


async def test_pipeline_worker_records_not_ready_heartbeat_for_bad_config() -> None:
    heartbeats = InMemoryWorkerHeartbeatRepository()

    with pytest.raises(
        typer.BadParameter, match="pipeline role requires CORTEX_EVENT_BUS=kafka"
    ):
        await run_worker(
            "pipeline",
            settings=Settings(cortex_event_bus="memory", cortex_state_backend="sql"),
            heartbeat_repository=heartbeats,
            instance_id="worker_2",
        )

    heartbeat = heartbeats.list_all()[0]
    assert heartbeat.role == "pipeline"
    assert heartbeat.instance_id == "worker_2"
    assert heartbeat.status == "not_ready"
    assert heartbeat.failure_reason == "pipeline role requires CORTEX_EVENT_BUS=kafka"
