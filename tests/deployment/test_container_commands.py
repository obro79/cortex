import pytest
import typer

from cortex.config import Settings
from cortex.workers.main import run_worker


async def test_noop_worker_role_exits_successfully() -> None:
    result = await run_worker("noop", settings=Settings())

    assert result == 0


async def test_invalid_worker_role_fails_clearly() -> None:
    with pytest.raises(typer.BadParameter, match="Unknown worker role: invalid"):
        await run_worker("invalid", settings=Settings())


async def test_pipeline_role_requires_kafka_event_bus() -> None:
    settings = Settings(cortex_event_bus="memory", cortex_state_backend="sql")

    with pytest.raises(
        typer.BadParameter, match="pipeline role requires CORTEX_EVENT_BUS=kafka"
    ):
        await run_worker("pipeline", settings=settings)


async def test_pipeline_role_requires_sql_state_backend() -> None:
    settings = Settings(cortex_event_bus="kafka", cortex_state_backend="memory")

    with pytest.raises(
        typer.BadParameter, match="pipeline role requires CORTEX_STATE_BACKEND=sql"
    ):
        await run_worker("pipeline", settings=settings)
