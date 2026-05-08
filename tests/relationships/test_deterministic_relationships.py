from __future__ import annotations

from datetime import UTC, datetime

from cortex.contracts.entities import SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.ingestion.payloads import sha256_digest
from cortex.relationships.parsers import DeterministicRelationshipParser
from cortex.relationships.service import DeterministicRelationshipBuilder


def make_object(
    provider: str,
    object_type: str,
    object_id: str,
    content: str,
    metadata: dict[str, object],
) -> SourceObject:
    now = datetime.now(UTC)
    return SourceObject(
        id=object_id,
        workspace_id="ws_1",
        source_connection_id=f"src_{provider}",
        provider=provider,
        object_type=object_type,
        external_object_id=object_id,
        external_object_key=f"{provider}:{object_id}",
        content_text=content,
        content_hash=sha256_digest(content.encode()),
        metadata_json=metadata,
        status=SourceObjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_parser_extracts_phase9_relationship_hints() -> None:
    hints = DeterministicRelationshipParser().parse_text(
        "COR-123 is fixed in #12 and docs/architecture/session.md via abc1234"
    )

    assert {hint.relationship_type for hint in hints} >= {
        "mentions_linear_issue",
        "mentions_github_pr",
        "mentions_commit",
        "mentions_doc_path",
        "mentions_file_path",
    }


def test_builder_links_known_objects_and_leaves_identity_mapping_out() -> None:
    linear = make_object(
        "linear",
        "linear_issue",
        "so_linear",
        "Work is in #12 and docs/architecture/session.md. User U123 reviewed it.",
        {"identifier": "COR-123"},
    )
    github = make_object(
        "github",
        "github_pull_request",
        "so_pr",
        "Fix COR-123",
        {"number": 12},
    )
    doc = make_object(
        "repo_docs",
        "repo_doc",
        "so_doc",
        "Session docs",
        {"path": "docs/architecture/session.md"},
    )

    result = DeterministicRelationshipBuilder().build(
        workspace_id="ws_1",
        source_objects=[linear, github, doc],
        raw_event_id="raw_1",
    )

    assert {(seed.from_id, seed.to_id) for seed in result.seeds} == {
        ("so_linear", "so_pr"),
        ("so_linear", "so_doc"),
        ("so_pr", "so_linear"),
    }
    assert not any("user" in seed.relationship_type for seed in result.seeds)
