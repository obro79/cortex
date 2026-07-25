from datetime import UTC, datetime

import pytest

from cortex.contracts.entities import SourceFile, SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.normalization.repositories import (
    InMemoryRelationshipSeedRepository,
    InMemorySourceFileRepository,
    InMemorySourceObjectRepository,
    SourceLifecycleError,
)
from cortex.normalization.result import RelationshipSeed


def source_object(content_hash: str = "sha256:one") -> SourceObject:
    now = datetime.now(UTC)
    return SourceObject(
        id="so_1",
        workspace_id="ws_1",
        source_connection_id="src_1",
        provider="linear",
        object_type="linear_issue",
        external_object_id="COR-123",
        external_object_key="linear:COR-123",
        title="COR-123",
        normalized_version="fixture-normalizer-v1",
        content_hash=content_hash,
        metadata_json={"fixture_id": "linear-issue-COR-123"},
        status=SourceObjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def source_file(content_hash: str = "sha256:file") -> SourceFile:
    now = datetime.now(UTC)
    return SourceFile(
        id="file_1",
        workspace_id="ws_1",
        source_object_id="so_1",
        source_connection_id="src_1",
        provider="slack",
        external_file_id="file_1",
        external_object_key="slack:file_1",
        file_name_hash="sha256:name",
        content_type="image/png",
        storage_ref="fixture://files/file_1",
        content_hash=content_hash,
        ocr_text="OCR text",
        ocr_text_hash=content_hash,
        metadata_json={"ocr_fixture": True},
        status=SourceObjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_source_object_upsert_inserts_noops_and_updates_by_external_identity() -> None:
    repository = InMemorySourceObjectRepository()

    inserted = repository.upsert_many([source_object()])
    noop = repository.upsert_many([source_object()])
    updated = repository.upsert_many([source_object("sha256:two")])

    assert inserted[0].operation == "inserted"
    assert noop[0].operation == "noop"
    assert updated[0].operation == "updated"
    assert updated[0].record.id == "so_1"
    assert (
        repository.get_by_external_identity(
            "ws_1", "linear", "linear_issue", "COR-123"
        ).content_hash
        == "sha256:two"
    )


def test_source_lifecycle_rejects_updates_after_deleted() -> None:
    repository = InMemorySourceObjectRepository()
    repository.upsert_many([source_object()])
    deleted = repository.mark_deleted("so_1")

    assert deleted.status == SourceObjectStatus.DELETED
    with pytest.raises(SourceLifecycleError):
        repository.mark_stale("so_1")


def test_source_file_upsert_uses_external_file_identity() -> None:
    repository = InMemorySourceFileRepository()

    inserted = repository.upsert_many([source_file()])
    noop = repository.upsert_many([source_file()])
    updated = repository.upsert_many([source_file("sha256:file2")])

    assert inserted[0].operation == "inserted"
    assert noop[0].operation == "noop"
    assert updated[0].operation == "updated"
    assert updated[0].record.ocr_text_hash == "sha256:file2"


def test_relationship_seed_replay_noops_existing_seed() -> None:
    repository = InMemoryRelationshipSeedRepository()
    seed = RelationshipSeed(
        id="rel_1",
        workspace_id="ws_1",
        relationship_type="mentions_issue",
        from_id="so_1",
        to_id="so_2",
        confidence=1,
        raw_event_id="raw_1",
        normalized_version="fixture-normalizer-v1",
    )

    first = repository.upsert_many([seed])
    second = repository.upsert_many([seed])

    assert first[0].operation == "inserted"
    assert second[0].operation == "noop"
    assert repository.list_all() == [seed]
