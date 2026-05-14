import asyncio
from typing import Annotated

import typer

from cortex.config import Settings
from cortex.db.session import create_sessionmaker
from cortex.events.kafka_admin import ensure_pipeline_topics
from cortex.observability.logging import setup_logging
from cortex.observability.tracing import init_tracing
from cortex.workers.factory import create_kafka_pipeline_consumer, pipeline_topics
from cortex.workers.heartbeat import (
    InMemoryWorkerHeartbeatRepository,
    default_worker_instance_id,
)
from cortex.workers.lifecycle import process_lifecycle_queue_once

app = typer.Typer(help="Cortex worker entrypoint")


async def run_worker(
    role: str,
    settings: Settings | None = None,
    heartbeat_repository: InMemoryWorkerHeartbeatRepository | None = None,
    instance_id: str | None = None,
) -> int:
    resolved = settings or Settings()
    setup_logging(resolved.cortex_log_level)
    init_tracing(f"cortex-worker-{role}")
    worker_instance_id = instance_id or default_worker_instance_id(role)
    if role == "noop":
        if heartbeat_repository is not None:
            heartbeat_repository.record(
                role=role, instance_id=worker_instance_id, status="ready"
            )
        return 0
    if role == "pipeline":
        if resolved.cortex_event_bus != "kafka":
            if heartbeat_repository is not None:
                heartbeat_repository.record(
                    role=role,
                    instance_id=worker_instance_id,
                    status="not_ready",
                    failure_reason="pipeline role requires CORTEX_EVENT_BUS=kafka",
                )
            raise typer.BadParameter("pipeline role requires CORTEX_EVENT_BUS=kafka")
        if resolved.cortex_state_backend != "sql":
            if heartbeat_repository is not None:
                heartbeat_repository.record(
                    role=role,
                    instance_id=worker_instance_id,
                    status="not_ready",
                    failure_reason="pipeline role requires CORTEX_STATE_BACKEND=sql",
                )
            raise typer.BadParameter("pipeline role requires CORTEX_STATE_BACKEND=sql")
        if heartbeat_repository is not None:
            heartbeat_repository.record(
                role=role, instance_id=worker_instance_id, status="starting"
            )
        await ensure_pipeline_topics(
            bootstrap_servers=resolved.kafka_bootstrap_servers,
        )
        session_factory = create_sessionmaker(resolved.database_url)
        consumer = create_kafka_pipeline_consumer(
            settings=resolved,
            session_factory=session_factory,
        )
        await consumer.run_forever(pipeline_topics())
        return 0
    if role == "lifecycle":
        if resolved.cortex_state_backend != "sql":
            if heartbeat_repository is not None:
                heartbeat_repository.record(
                    role=role,
                    instance_id=worker_instance_id,
                    status="not_ready",
                    failure_reason="lifecycle role requires CORTEX_STATE_BACKEND=sql",
                )
            raise typer.BadParameter("lifecycle role requires CORTEX_STATE_BACKEND=sql")
        if not resolved.database_url:
            if heartbeat_repository is not None:
                heartbeat_repository.record(
                    role=role,
                    instance_id=worker_instance_id,
                    status="not_ready",
                    failure_reason="lifecycle role requires DATABASE_URL",
                )
            raise typer.BadParameter("lifecycle role requires DATABASE_URL")
        if heartbeat_repository is not None:
            heartbeat_repository.record(
                role=role, instance_id=worker_instance_id, status="starting"
            )
        session_factory = create_sessionmaker(resolved.database_url)
        await process_lifecycle_queue_once(
            settings=resolved,
            session_factory=session_factory,
            worker_id=worker_instance_id,
        )
        if heartbeat_repository is not None:
            heartbeat_repository.record(
                role=role, instance_id=worker_instance_id, status="ready"
            )
        return 0
    raise typer.BadParameter(f"Unknown worker role: {role}")


@app.callback(invoke_without_command=True)
def main(
    role: Annotated[str, typer.Option(help="Worker role to run")] = "noop",
) -> None:
    raise typer.Exit(asyncio.run(run_worker(role)))
