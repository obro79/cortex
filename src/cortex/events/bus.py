from collections.abc import Mapping
from typing import Any, Protocol

from cortex.contracts.pipeline_events import PipelineEventEnvelope


class EventBus(Protocol):
    async def publish(self, event: PipelineEventEnvelope) -> None: ...


TOPIC_BY_EVENT_TYPE: Mapping[str, str] = {
    "raw_event.persisted": "pipeline.raw-events",
    "source_object.upserted": "pipeline.source-objects",
    "source_object.deleted": "pipeline.source-objects",
    "source_file.fetched": "pipeline.source-files",
    "source_chunk.upserted": "pipeline.source-chunks",
    "source_chunk.deleted": "pipeline.source-chunks",
    "embedding.requested": "pipeline.embeddings",
    "embedding.completed": "pipeline.embeddings",
    "index.requested": "pipeline.indexes",
    "index.completed": "pipeline.indexes",
    "semantic_artifact.upserted": "pipeline.artifacts",
    "relationship.upserted": "pipeline.relationships",
    "evidence_pack.created": "pipeline.retrieval",
    "context_gate.completed": "pipeline.context-gate",
    "canonical_decision.approved": "pipeline.canonical-memory",
    "deletion.requested": "pipeline.deletions",
    "deletion.completed": "pipeline.deletions",
}

PIPELINE_TOPICS: tuple[str, ...] = tuple(sorted(set(TOPIC_BY_EVENT_TYPE.values())))
DEADLETTER_TOPIC = "pipeline.deadletters"


class UnsupportedPipelineEventType(ValueError):
    pass


def topic_for_event_type(event_type: str) -> str:
    try:
        return TOPIC_BY_EVENT_TYPE[event_type]
    except KeyError as error:
        raise UnsupportedPipelineEventType(event_type) from error


class KafkaEventBus:
    def __init__(
        self,
        *,
        bootstrap_servers: str,
        producer: Any | None = None,
        client_id: str = "cortex-api",
    ) -> None:
        if not bootstrap_servers:
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS is required")
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self._producer = producer
        self._owns_producer = producer is None
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        if self._producer is None:
            try:
                from aiokafka import AIOKafkaProducer
            except ImportError as error:  # pragma: no cover - environment guard
                raise RuntimeError("aiokafka is required for KafkaEventBus") from error
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
            )
        await self._producer.start()
        self._started = True

    async def stop(self) -> None:
        if self._started and self._producer is not None and self._owns_producer:
            await self._producer.stop()
        self._started = False

    async def publish(self, event: PipelineEventEnvelope) -> None:
        topic = topic_for_event_type(event.event_type)
        await self.start()
        if self._producer is None:
            raise RuntimeError("Kafka producer is not initialized")
        await self._producer.send_and_wait(
            topic,
            event.model_dump_json().encode("utf-8"),
            key=event.partition_key.encode("utf-8"),
            headers=(
                ("event_id", event.event_id.encode("utf-8")),
                ("schema_version", event.schema_version.encode("utf-8")),
            ),
        )
