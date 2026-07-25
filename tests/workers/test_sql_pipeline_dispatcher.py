from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from cortex.config import Settings
from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.embeddings.gemini import GeminiEmbeddingProvider
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import FilePayloadStore
from cortex.workers.factory import SqlPipelineDispatcher, create_kafka_pipeline_consumer
from cortex.workers.kafka import RetryablePipelineError


@dataclass
class FakeSession:
    calls: list[str]

    async def commit(self) -> None:
        self.calls.append("commit")

    async def rollback(self) -> None:
        self.calls.append("rollback")


class FakeSessionContext:
    def __init__(self, calls: list[str]) -> None:
        self.session = FakeSession(calls)

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeSessionFactory:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def __call__(self) -> FakeSessionContext:
        return FakeSessionContext(self.calls)


class FakeKafkaBus:
    def __init__(self, calls: list[str], *, fail: bool = False) -> None:
        self.calls = calls
        self.fail = fail

    async def publish(self, event: PipelineEventEnvelope) -> None:
        self.calls.append(f"publish:{event.event_type}")
        if self.fail:
            raise RuntimeError("publish failed")

    async def stop(self) -> None:
        self.calls.append("stop")


def envelope(event_type: str = "raw_event.persisted") -> PipelineEventEnvelope:
    return PipelineEventEnvelope(
        event_id="evt_1",
        event_type=event_type,
        occurred_at=datetime.now(UTC),
        published_at=datetime.now(UTC),
        workspace_id="ws_1",
        partition_key="ws_1:key",
        subject={"type": "raw_event", "id": "raw_1"},
        trace={"trace_id": "trace_1"},
    )


async def test_sql_dispatcher_commits_before_publishing_buffered_events(
    tmp_path,
    monkeypatch,
) -> None:
    calls: list[str] = []
    dispatcher = SqlPipelineDispatcher(
        session_factory=FakeSessionFactory(calls),  # type: ignore[arg-type]
        payload_store=FilePayloadStore(tmp_path),
        event_bus=FakeKafkaBus(calls),  # type: ignore[arg-type]
        settings=Settings(),
    )

    async def fake_dispatch(session, incoming, event_bus) -> object:
        calls.append(f"dispatch:{incoming.event_type}")
        await event_bus.publish(envelope("source_object.upserted"))
        return SimpleNamespace(status="processed")

    monkeypatch.setattr(dispatcher, "_dispatch", fake_dispatch)
    bus = InMemoryEventBus()
    bus.events.append(envelope())

    await dispatcher.drain(bus)

    assert calls == [
        "dispatch:raw_event.persisted",
        "commit",
        "publish:source_object.upserted",
    ]


def test_sql_dispatcher_uses_gemini_provider_when_embedding_mode_is_real(
    tmp_path,
) -> None:
    dispatcher = SqlPipelineDispatcher(
        session_factory=FakeSessionFactory([]),  # type: ignore[arg-type]
        payload_store=FilePayloadStore(tmp_path),
        event_bus=FakeKafkaBus([]),  # type: ignore[arg-type]
        settings=Settings(
            _env_file=None,
            cortex_embedding_mode="real",
            gemini_api_key="test-key",
        ),
    )

    provider = dispatcher._embedding_provider()

    assert isinstance(provider, GeminiEmbeddingProvider)
    assert provider.api_key == "test-key"
    assert provider.model == "gemini-embedding-2"
    assert provider.dimensions == 1536


async def test_sql_dispatcher_retryable_result_commits_state_but_not_publish_or_ack(
    tmp_path,
    monkeypatch,
) -> None:
    calls: list[str] = []
    dispatcher = SqlPipelineDispatcher(
        session_factory=FakeSessionFactory(calls),  # type: ignore[arg-type]
        payload_store=FilePayloadStore(tmp_path),
        event_bus=FakeKafkaBus(calls),  # type: ignore[arg-type]
        settings=Settings(),
    )

    async def fake_dispatch(session, incoming, event_bus) -> object:
        calls.append(f"dispatch:{incoming.event_type}")
        await event_bus.publish(envelope("source_object.upserted"))
        return SimpleNamespace(status="retryable")

    monkeypatch.setattr(dispatcher, "_dispatch", fake_dispatch)
    bus = InMemoryEventBus()
    bus.events.append(envelope())

    with pytest.raises(RetryablePipelineError):
        await dispatcher.drain(bus)

    assert calls == ["dispatch:raw_event.persisted", "commit"]


async def test_sql_dispatcher_downstream_publish_failure_is_retryable(
    tmp_path,
    monkeypatch,
) -> None:
    calls: list[str] = []
    dispatcher = SqlPipelineDispatcher(
        session_factory=FakeSessionFactory(calls),  # type: ignore[arg-type]
        payload_store=FilePayloadStore(tmp_path),
        event_bus=FakeKafkaBus(calls, fail=True),  # type: ignore[arg-type]
        settings=Settings(),
    )

    async def fake_dispatch(session, incoming, event_bus) -> object:
        calls.append(f"dispatch:{incoming.event_type}")
        await event_bus.publish(envelope("source_object.upserted"))
        return SimpleNamespace(status="processed")

    monkeypatch.setattr(dispatcher, "_dispatch", fake_dispatch)
    bus = InMemoryEventBus()
    bus.events.append(envelope())

    with pytest.raises(RetryablePipelineError):
        await dispatcher.drain(bus)

    assert calls == [
        "dispatch:raw_event.persisted",
        "commit",
        "publish:source_object.upserted",
    ]


def test_pipeline_consumer_requires_qdrant_when_no_index_is_injected() -> None:
    with pytest.raises(ValueError, match="QDRANT_URL is required"):
        create_kafka_pipeline_consumer(
            settings=Settings(
                cortex_event_bus="kafka",
                cortex_state_backend="sql",
                kafka_bootstrap_servers="localhost:9092",
                database_url="postgresql+asyncpg://localhost/cortex",
            ),
            session_factory=FakeSessionFactory([]),  # type: ignore[arg-type]
        )
