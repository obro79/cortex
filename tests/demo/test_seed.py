from __future__ import annotations

from cortex.contracts.enums import RawEventStatus
from cortex.demo.golden_incident import load_golden_incident_manifest
from cortex.demo.seed import InMemoryDemoRuntime, mark_raw_events_deleted, reset_scope
from cortex.ingestion.raw_events import RawEventInput


async def test_seed_is_idempotent_and_releases_only_requested_phase() -> None:
    manifest = load_golden_incident_manifest()
    runtime = InMemoryDemoRuntime(manifest)

    first = await runtime.seed(phase="pre_live")
    second = await runtime.seed(phase="pre_live")
    post_live = await runtime.seed(phase="post_live")

    assert first.created_count == len(manifest.pre_live_inputs())
    assert second.created_count == 0
    assert second.existing_count == len(manifest.pre_live_inputs())
    assert post_live.created_count == 1
    assert post_live.existing_count == len(manifest.pre_live_inputs())
    assert len(runtime.event_bus.list_events()) == len(manifest.records)


async def test_in_memory_reset_replaces_only_the_fixture_runtime() -> None:
    manifest = load_golden_incident_manifest()
    runtime = InMemoryDemoRuntime(manifest)
    await runtime.seed(phase="post_live")

    scope = await runtime.reset()

    assert scope.workspace_id == manifest.workspace_id
    assert len(scope.raw_event_ids) == len(manifest.records)
    assert runtime.repository.list_all() == []
    reseeded = await runtime.seed(phase="post_live")
    assert reseeded.created_count == len(manifest.records)


async def test_raw_event_tombstone_scope_does_not_touch_other_workspace() -> None:
    manifest = load_golden_incident_manifest()
    runtime = InMemoryDemoRuntime(manifest)
    await runtime.seed(phase="post_live")
    unrelated = RawEventInput(
        workspace_id=manifest.workspace_id,
        source_connection_id="src_fixture",
        provider="fixture",
        external_event_id="unrelated",
        event_type="fixture.created",
        external_object_key="fixture:unrelated",
        idempotency_key="fixture:unrelated",
        payload={"fixture_id": "unrelated"},
    )
    unrelated_result = await runtime.ingestion.ingest(unrelated)
    assert await mark_raw_events_deleted(
        repository=runtime.repository, scope=reset_scope(manifest)
    ) == len(manifest.records)
    remaining = runtime.repository.get_by_id(unrelated_result.raw_event_id)
    assert remaining.status == RawEventStatus.PUBLISHED
