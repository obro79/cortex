from cortex.events.kafka_admin import ensure_pipeline_topics


class FakeAdmin:
    def __init__(self, existing: set[str] | None = None) -> None:
        self.existing = existing or set()
        self.created: list[object] = []

    async def list_topics(self) -> set[str]:
        return self.existing

    async def create_topics(self, topics: list[object], validate_only: bool) -> None:
        self.created = topics


async def test_ensure_pipeline_topics_creates_missing_topics() -> None:
    admin = FakeAdmin(existing={"pipeline.raw-events"})

    created = await ensure_pipeline_topics(
        bootstrap_servers="localhost:9092",
        admin_client=admin,
    )

    assert "pipeline.raw-events" not in created
    assert "pipeline.deadletters" in created
    assert all(topic.replication_factor == 1 for topic in admin.created)
