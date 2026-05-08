from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cortex.events.bus import DEADLETTER_TOPIC, PIPELINE_TOPICS


@dataclass(frozen=True)
class KafkaTopicSpec:
    name: str
    partitions: int = 3
    replication_factor: int = 1


@dataclass(frozen=True)
class TopicCreateRequest:
    name: str
    num_partitions: int
    replication_factor: int


def default_topic_specs() -> list[KafkaTopicSpec]:
    return [
        KafkaTopicSpec(name=topic) for topic in (*PIPELINE_TOPICS, DEADLETTER_TOPIC)
    ]


async def ensure_pipeline_topics(
    *,
    bootstrap_servers: str,
    admin_client: Any | None = None,
    topics: list[KafkaTopicSpec] | None = None,
) -> list[str]:
    specs = topics or default_topic_specs()
    new_topic_factory: Any
    if admin_client is None:
        try:
            from aiokafka.admin import AIOKafkaAdminClient, NewTopic
        except ImportError as error:  # pragma: no cover - environment guard
            raise RuntimeError(
                "aiokafka is required to provision Kafka topics"
            ) from error
        admin_client = AIOKafkaAdminClient(bootstrap_servers=bootstrap_servers)
        new_topic_factory = NewTopic
        owns_client = True
    else:
        new_topic_factory = TopicCreateRequest
        owns_client = False

    if owns_client:
        await admin_client.start()
    try:
        existing = set(await admin_client.list_topics())
        missing = [spec for spec in specs if spec.name not in existing]
        if not missing:
            return []
        await admin_client.create_topics(
            [
                new_topic_factory(
                    name=spec.name,
                    num_partitions=spec.partitions,
                    replication_factor=spec.replication_factor,
                )
                for spec in missing
            ],
            validate_only=False,
        )
        return [spec.name for spec in missing]
    finally:
        if owns_client:
            await admin_client.close()
