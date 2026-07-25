import asyncio
from typing import Annotated

import typer

from cortex.config import Settings
from cortex.db.session import create_sessionmaker
from cortex.events.kafka_admin import ensure_pipeline_topics
from cortex.observability.logging import setup_logging
from cortex.observability.tracing import init_tracing
from cortex.workers.factory import create_kafka_pipeline_consumer, pipeline_topics

app = typer.Typer(help="Cortex worker entrypoint")


async def run_worker(role: str, settings: Settings | None = None) -> int:
    resolved = settings or Settings()
    setup_logging(resolved.cortex_log_level)
    init_tracing(f"cortex-worker-{role}")
    if role == "noop":
        return 0
    if role == "pipeline":
        if resolved.cortex_event_bus != "kafka":
            raise typer.BadParameter("pipeline role requires CORTEX_EVENT_BUS=kafka")
        if resolved.cortex_state_backend != "sql":
            raise typer.BadParameter("pipeline role requires CORTEX_STATE_BACKEND=sql")
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
    raise typer.BadParameter(f"Unknown worker role: {role}")


@app.callback(invoke_without_command=True)
def main(
    role: Annotated[str, typer.Option(help="Worker role to run")] = "noop",
) -> None:
    raise typer.Exit(asyncio.run(run_worker(role)))
