from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from cortex.contracts.pipeline_events import (
    PipelineEventEnvelope,
    PipelineSubject,
    PipelineTrace,
)
from cortex.events.bus import DEADLETTER_TOPIC
from cortex.events.in_memory import InMemoryEventBus
from cortex.events.kafka_admin import ensure_pipeline_topics
from cortex.workers.pipeline import InMemoryPipelineDispatcher


@dataclass(frozen=True)
class KafkaConsumerResult:
    status: str
    event_type: str | None = None
    event_id: str | None = None
    reason: str | None = None


class KafkaPipelineConsumer:
    def __init__(
        self,
        *,
        bootstrap_servers: str,
        group_id: str,
        dispatcher: InMemoryPipelineDispatcher,
        consumer: Any | None = None,
        producer: Any | None = None,
        client_id: str = "cortex-pipeline-worker",
    ) -> None:
        if not bootstrap_servers:
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS is required")
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.dispatcher = dispatcher
        self.consumer = consumer
        self.producer = producer
        self.client_id = client_id
        self._owns_clients = consumer is None or producer is None

    async def start(self, topics: tuple[str, ...]) -> None:
        if self.consumer is None or self.producer is None:
            try:
                from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
            except ImportError as error:  # pragma: no cover - environment guard
                raise RuntimeError(
                    "aiokafka is required for Kafka consumers"
                ) from error
            self.consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                enable_auto_commit=False,
                client_id=self.client_id,
            )
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=f"{self.client_id}-deadletters",
            )
        await self.consumer.start()
        await self.producer.start()

    async def stop(self) -> None:
        if self.consumer is not None:
            await self.consumer.stop()
        if self.producer is not None:
            await self.producer.stop()

    async def run_forever(self, topics: tuple[str, ...]) -> None:
        await ensure_pipeline_topics(bootstrap_servers=self.bootstrap_servers)
        await self.start(topics)
        if self.consumer is None:
            raise RuntimeError("Kafka consumer is not initialized")
        try:
            async for message in self.consumer:
                await self.handle_message(message)
        finally:
            await self.stop()

    async def handle_message(self, message: Any) -> KafkaConsumerResult:
        try:
            envelope = PipelineEventEnvelope.model_validate_json(message.value)
        except ValidationError as error:
            await self._publish_deadletter(
                message=message,
                error_code="invalid_envelope",
                error_message=type(error).__name__,
            )
            if self.consumer is None:
                raise RuntimeError("Kafka consumer is not initialized") from error
            await self.consumer.commit()
            return KafkaConsumerResult(status="deadlettered", reason="invalid_envelope")

        try:
            await self._dispatch(envelope)
        except Exception as error:
            await self._publish_deadletter(
                message=message,
                envelope=envelope,
                error_code="handler_failed",
                error_message=type(error).__name__,
            )
            if self.consumer is None:
                raise RuntimeError("Kafka consumer is not initialized") from error
            await self.consumer.commit()
            return KafkaConsumerResult(
                status="deadlettered",
                event_type=envelope.event_type,
                event_id=envelope.event_id,
                reason="handler_failed",
            )

        if self.consumer is None:
            raise RuntimeError("Kafka consumer is not initialized")
        await self.consumer.commit()
        return KafkaConsumerResult(
            status="processed",
            event_type=envelope.event_type,
            event_id=envelope.event_id,
        )

    async def _dispatch(self, envelope: PipelineEventEnvelope) -> None:
        event_bus = InMemoryEventBus()
        event_bus.events.append(envelope)
        await self.dispatcher.drain(event_bus)

    async def _publish_deadletter(
        self,
        *,
        message: Any,
        error_code: str,
        error_message: str,
        envelope: PipelineEventEnvelope | None = None,
    ) -> None:
        payload = {
            "source_topic": str(getattr(message, "topic", "")),
            "source_partition": int(getattr(message, "partition", 0)),
            "source_offset": int(getattr(message, "offset", 0)),
            "error_code": error_code,
            "error_message": error_message,
        }
        if envelope is not None:
            payload.update(
                {
                    "event_id": envelope.event_id,
                    "event_type": envelope.event_type,
                    "workspace_id": envelope.workspace_id,
                    "subject_type": envelope.subject.type,
                    "subject_id": envelope.subject.id,
                }
            )
        if self.producer is None:
            raise RuntimeError("Kafka producer is not initialized")
        await self.producer.send_and_wait(
            DEADLETTER_TOPIC,
            PipelineEventEnvelope(
                event_id=f"evt_deadletter_{getattr(message, 'offset', 0)}",
                event_type="pipeline.deadlettered",
                workspace_id=envelope.workspace_id if envelope else "unknown",
                partition_key=envelope.partition_key if envelope else "unknown",
                subject=PipelineSubject(
                    type="pipeline_message",
                    id=envelope.event_id if envelope else "unknown",
                ),
                trace=PipelineTrace(
                    trace_id=envelope.trace.trace_id if envelope else "unknown"
                ),
                payload=payload,
            )
            .model_dump_json()
            .encode("utf-8"),
            key=(envelope.partition_key if envelope else "unknown").encode("utf-8"),
        )


PipelineFactory = Callable[[], Awaitable[InMemoryPipelineDispatcher]]
