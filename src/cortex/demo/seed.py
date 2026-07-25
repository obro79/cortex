"""Deterministic, fixture-scoped COR-123 raw-event preparation.

This module deliberately has no database, vector-index, or provider client
dependency.  A caller supplies the normal runtime ingestion service, keeping
the mutating boundary explicit and allowing the same corpus to be exercised in
memory during tests and rehearsals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository, RawEventInput
from cortex.ingestion.service import IngestionResult, RawEventIngestionService
from cortex.utils.asyncio import maybe_await

from .golden_incident import GoldenIncidentManifest

DemoPhase = Literal["pre_live", "post_live"]
IDEMPOTENCY_PREFIX = "golden-incident:"


class DemoSeedError(ValueError):
    """Raised when an input cannot safely be treated as demo fixture data."""


class DemoIngestion(Protocol):
    async def ingest(self, item: RawEventInput) -> IngestionResult: ...


@dataclass(frozen=True)
class DemoResetScope:
    """Exact identifiers a runtime reset executor may affect.

    The scope never means "delete this workspace".  It includes the fixed raw
    event ids and external-object keys so a durable executor can cascade only
    the synthetic corpus' derived records and vector points.
    """

    workspace_id: str
    task_ref: str
    manifest_sha256: str
    raw_event_ids: frozenset[str]
    external_object_keys: frozenset[str]
    idempotency_keys: frozenset[str]


@dataclass(frozen=True)
class DemoSeedResult:
    phase: DemoPhase
    selected_record_count: int
    created_count: int
    existing_count: int
    published_count: int
    raw_event_ids: tuple[str, ...]


def inputs_for_phase(
    manifest: GoldenIncidentManifest, phase: DemoPhase
) -> tuple[RawEventInput, ...]:
    pre_live = manifest.pre_live_inputs()
    if phase == "pre_live":
        selected = pre_live
    elif phase == "post_live":
        selected = (*pre_live, manifest.live_input())
    else:  # Defensive for callers outside the typed API.
        raise DemoSeedError(f"unsupported demo phase: {phase}")
    _validate_inputs(manifest, selected)
    return selected


def reset_scope(manifest: GoldenIncidentManifest) -> DemoResetScope:
    inputs = inputs_for_phase(manifest, "post_live")
    return DemoResetScope(
        workspace_id=manifest.workspace_id,
        task_ref=manifest.task_ref,
        manifest_sha256=manifest.sha256,
        raw_event_ids=frozenset(
            item.raw_event_id for item in inputs if item.raw_event_id is not None
        ),
        external_object_keys=frozenset(item.external_object_key for item in inputs),
        idempotency_keys=frozenset(item.idempotency_key for item in inputs),
    )


class DemoCorpusSeeder:
    """Seed one deterministic corpus through the application's ingestion port."""

    def __init__(self, *, manifest: GoldenIncidentManifest, ingestion: DemoIngestion):
        self.manifest = manifest
        self.ingestion = ingestion

    async def seed(self, *, phase: DemoPhase = "pre_live") -> DemoSeedResult:
        results = [
            await self.ingestion.ingest(item)
            for item in inputs_for_phase(self.manifest, phase)
        ]
        return DemoSeedResult(
            phase=phase,
            selected_record_count=len(results),
            created_count=sum(result.created for result in results),
            existing_count=sum(not result.created for result in results),
            published_count=sum(result.published for result in results),
            raw_event_ids=tuple(result.raw_event_id for result in results),
        )


class InMemoryDemoRuntime:
    """A disposable runtime for rehearsal and validation of the seed contract.

    Reset replaces only this fixture runtime.  It intentionally cannot reset a
    shared SQL/Qdrant deployment; production callers must provide a reviewed
    executor that consumes :func:`reset_scope`.
    """

    def __init__(self, manifest: GoldenIncidentManifest) -> None:
        self.manifest = manifest
        self._build_runtime()

    def _build_runtime(self) -> None:
        self.repository = InMemoryRawEventRepository()
        self.payload_store = InMemoryPayloadStore()
        self.event_bus = InMemoryEventBus()
        self.ingestion = RawEventIngestionService(
            self.repository,
            self.payload_store,
            RawEventPublisher(self.event_bus),
        )
        self.seeder = DemoCorpusSeeder(
            manifest=self.manifest, ingestion=self.ingestion
        )

    async def seed(self, *, phase: DemoPhase = "pre_live") -> DemoSeedResult:
        return await self.seeder.seed(phase=phase)

    async def reset(self) -> DemoResetScope:
        scope = reset_scope(self.manifest)
        self._build_runtime()
        return scope


async def mark_raw_events_deleted(
    *, repository: Any, scope: DemoResetScope
) -> int:
    """Apply the narrow raw-event tombstone portion of a reset.

    This is useful for a lifecycle executor, but is not a complete durable
    reset: source objects, chunks, and vector points must be cascaded using the
    same ``scope`` before a corpus can be seeded anew.
    """

    deleted = await maybe_await(
        repository.mark_deleted_for_lifecycle(
            workspace_id=scope.workspace_id,
            raw_event_ids=set(scope.raw_event_ids),
            external_object_keys=set(scope.external_object_keys),
        )
    )
    return len(deleted)


def _validate_inputs(
    manifest: GoldenIncidentManifest, inputs: tuple[RawEventInput, ...]
) -> None:
    if not inputs:
        raise DemoSeedError("demo seed input set is empty")
    seen_keys: set[str] = set()
    for item in inputs:
        if item.workspace_id != manifest.workspace_id:
            raise DemoSeedError("demo input workspace does not match manifest")
        if not item.idempotency_key.startswith(IDEMPOTENCY_PREFIX):
            raise DemoSeedError("demo input idempotency key is outside fixture scope")
        if item.idempotency_key in seen_keys:
            raise DemoSeedError("demo input idempotency keys must be unique")
        seen_keys.add(item.idempotency_key)
        if not item.source_connection_id.startswith("src_demo_"):
            raise DemoSeedError("demo input source connection is outside fixture scope")
        if (
            not isinstance(item.payload, dict)
            or item.payload.get("synthetic_demo") is not True
        ):
            raise DemoSeedError("demo input must be explicitly synthetic")
        if item.payload.get("manifest_sha256") != manifest.sha256:
            raise DemoSeedError("demo input manifest hash does not match manifest")
