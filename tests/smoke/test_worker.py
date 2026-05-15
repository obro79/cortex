from types import SimpleNamespace

from typer.testing import CliRunner

from cortex.config import Settings
from cortex.workers.main import app, run_worker


async def test_run_noop_worker() -> None:
    assert await run_worker("noop") == 0


def test_worker_cli_noop(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--role", "noop"])
    assert result.exit_code == 0


async def test_pipeline_worker_requires_sql_state_backend() -> None:
    settings = Settings(
        cortex_event_bus="kafka",
        cortex_state_backend="memory",
        kafka_bootstrap_servers="localhost:9092",
        database_url="postgresql+asyncpg://localhost/cortex",
    )

    try:
        await run_worker("pipeline", settings)
    except Exception as error:
        assert "CORTEX_STATE_BACKEND=sql" in str(error)
    else:
        raise AssertionError("pipeline worker should reject memory state backend")


async def test_lifecycle_worker_requires_sql_state_backend() -> None:
    settings = Settings(
        cortex_state_backend="memory",
        database_url="postgresql+asyncpg://localhost/cortex",
    )

    try:
        await run_worker("lifecycle", settings)
    except Exception as error:
        assert "CORTEX_STATE_BACKEND=sql" in str(error)
    else:
        raise AssertionError("lifecycle worker should reject memory state backend")


async def test_provider_acl_worker_requires_sql_state_backend() -> None:
    settings = Settings(
        cortex_state_backend="memory",
        database_url="postgresql+asyncpg://localhost/cortex",
    )

    try:
        await run_worker("provider-acl", settings)
    except Exception as error:
        assert "CORTEX_STATE_BACKEND=sql" in str(error)
    else:
        raise AssertionError("provider-acl worker should reject memory state backend")


async def test_pipeline_worker_runs_consumer_loop(monkeypatch) -> None:
    calls: list[object] = []

    async def fake_ensure_pipeline_topics(*, bootstrap_servers: str) -> None:
        calls.append(("topics", bootstrap_servers))

    def fake_create_sessionmaker(database_url: str) -> object:
        calls.append(("sessionmaker", database_url))
        return object()

    class FakeConsumer:
        async def run_forever(self, topics: tuple[str, ...]) -> None:
            calls.append(("run_forever", topics))

    def fake_create_kafka_pipeline_consumer(*, settings: Settings, session_factory):
        calls.append(("consumer", settings.kafka_bootstrap_servers, session_factory))
        return FakeConsumer()

    monkeypatch.setattr(
        "cortex.workers.main.ensure_pipeline_topics",
        fake_ensure_pipeline_topics,
    )
    monkeypatch.setattr(
        "cortex.workers.main.create_sessionmaker",
        fake_create_sessionmaker,
    )
    monkeypatch.setattr(
        "cortex.workers.main.create_kafka_pipeline_consumer",
        fake_create_kafka_pipeline_consumer,
    )

    result = await run_worker(
        "pipeline",
        Settings(
            cortex_event_bus="kafka",
            cortex_state_backend="sql",
            kafka_bootstrap_servers="localhost:9092",
            database_url="postgresql+asyncpg://localhost/cortex",
        ),
    )

    assert result == 0
    assert calls[0] == ("topics", "localhost:9092")
    assert calls[1] == ("sessionmaker", "postgresql+asyncpg://localhost/cortex")
    assert calls[2][0] == "consumer"
    assert calls[3][0] == "run_forever"


async def test_lifecycle_worker_processes_queue_once(monkeypatch) -> None:
    calls: list[object] = []

    def fake_create_sessionmaker(database_url: str) -> object:
        calls.append(("sessionmaker", database_url))
        return object()

    async def fake_process_lifecycle_queue_once(
        *,
        settings: Settings,
        session_factory: object,
        worker_id: str,
    ) -> object:
        calls.append(("lifecycle", settings.database_url, session_factory, worker_id))
        return object()

    monkeypatch.setattr(
        "cortex.workers.main.create_sessionmaker",
        fake_create_sessionmaker,
    )
    monkeypatch.setattr(
        "cortex.workers.main.process_lifecycle_queue_once",
        fake_process_lifecycle_queue_once,
    )

    result = await run_worker(
        "lifecycle",
        Settings(
            cortex_state_backend="sql",
            database_url="postgresql+asyncpg://localhost/cortex",
        ),
        instance_id="lifecycle_1",
    )

    assert result == 0
    assert calls[0] == ("sessionmaker", "postgresql+asyncpg://localhost/cortex")
    assert calls[1][0] == "lifecycle"
    assert calls[1][3] == "lifecycle_1"


async def test_provider_acl_worker_processes_refresh_once(monkeypatch) -> None:
    calls: list[object] = []

    def fake_create_sessionmaker(database_url: str) -> object:
        calls.append(("sessionmaker", database_url))
        return object()

    async def fake_process_provider_acl_refresh_once(
        *,
        settings: Settings,
        session_factory: object,
        worker_id: str,
    ) -> object:
        calls.append(
            ("provider-acl", settings.database_url, session_factory, worker_id)
        )
        return SimpleNamespace(
            scheduler=SimpleNamespace(status="completed", error=None)
        )

    monkeypatch.setattr(
        "cortex.workers.main.create_sessionmaker",
        fake_create_sessionmaker,
    )
    monkeypatch.setattr(
        "cortex.workers.main.process_provider_acl_refresh_once",
        fake_process_provider_acl_refresh_once,
    )

    result = await run_worker(
        "provider-acl",
        Settings(
            cortex_state_backend="sql",
            database_url="postgresql+asyncpg://localhost/cortex",
        ),
        instance_id="provider_acl_1",
    )

    assert result == 0
    assert calls[0] == ("sessionmaker", "postgresql+asyncpg://localhost/cortex")
    assert calls[1][0] == "provider-acl"
    assert calls[1][3] == "provider_acl_1"


async def test_provider_acl_worker_fails_when_scheduled_job_fails(
    monkeypatch,
) -> None:
    def fake_create_sessionmaker(database_url: str) -> object:
        return object()

    async def fake_process_provider_acl_refresh_once(
        *,
        settings: Settings,
        session_factory: object,
        worker_id: str,
    ) -> object:
        return SimpleNamespace(
            scheduler=SimpleNamespace(status="failed", error="RuntimeError")
        )

    monkeypatch.setattr(
        "cortex.workers.main.create_sessionmaker",
        fake_create_sessionmaker,
    )
    monkeypatch.setattr(
        "cortex.workers.main.process_provider_acl_refresh_once",
        fake_process_provider_acl_refresh_once,
    )

    try:
        await run_worker(
            "provider-acl",
            Settings(
                cortex_state_backend="sql",
                database_url="postgresql+asyncpg://localhost/cortex",
            ),
            instance_id="provider_acl_1",
        )
    except RuntimeError as error:
        assert "provider ACL refresh failed" in str(error)
    else:
        raise AssertionError("provider ACL worker should fail on scheduler failure")
