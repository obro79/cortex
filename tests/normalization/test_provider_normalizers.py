from __future__ import annotations

from datetime import UTC, datetime

from cortex.contracts.entities import RawEvent
from cortex.contracts.enums import RawEventStatus
from cortex.ingestion.payloads import canonical_json_bytes
from cortex.normalization.normalizers.github import normalize_github_payload
from cortex.normalization.normalizers.linear import normalize_linear_payload
from cortex.normalization.normalizers.repo_docs import normalize_repo_doc_payload
from cortex.normalization.registry import NormalizerRegistry


def raw_event(provider: str) -> RawEvent:
    now = datetime.now(UTC)
    return RawEvent(
        id=f"raw_{provider}",
        workspace_id="ws_1",
        source_connection_id=f"src_{provider}",
        provider=provider,
        external_event_id=f"evt_{provider}",
        event_type=f"{provider}.event",
        external_object_key=f"{provider}:object",
        idempotency_key=f"{provider}:1",
        payload_ref="memory://payload",
        payload_hash="sha256:payload",
        received_at=now,
        status=RawEventStatus.PUBLISHED,
        trace_id="trace_1",
        created_at=now,
        updated_at=now,
    )


def test_linear_payload_normalizes_to_issue_object_without_text_metadata() -> None:
    result = normalize_linear_payload(
        raw_event("linear"),
        canonical_json_bytes(
            {
                "issue": {
                    "id": "lin_123",
                    "identifier": "COR-123",
                    "title": "Move sessions to Postgres",
                    "description": "Use Postgres as the session source of truth.",
                    "url": "https://linear.app/cortex/issue/COR-123",
                    "team": {"id": "team_1", "name": "Core"},
                    "project": {"id": "proj_1", "name": "Cortex"},
                    "state": {"id": "state_1", "name": "In Progress"},
                    "comments": [{"id": "c1", "body": "Slack agreed Redis is stale."}],
                }
            }
        ),
    )

    source_object = result.source_objects[0]

    assert result.normalized_version == "linear-normalizer-v1"
    assert source_object.object_type == "linear_issue"
    assert source_object.external_object_key == "linear:COR-123"
    assert "Postgres" in (source_object.content_text or "")
    assert "description" not in source_object.metadata_json
    assert source_object.metadata_json["identifier"] == "COR-123"


def test_github_payload_normalizes_pr_with_changed_file_metadata_only() -> None:
    result = normalize_github_payload(
        raw_event("github"),
        canonical_json_bytes(
            {
                "repository": {"id": 44, "full_name": "private/cortex"},
                "pull_request": {
                    "id": 555,
                    "number": 12,
                    "title": "Fix COR-123 session storage",
                    "body": "Implements the Linear task.",
                    "html_url": "https://github.com/private/cortex/pull/12",
                    "user": {"id": 99},
                },
                "comments": [{"id": 1, "body": "Docs need an update."}],
                "changed_files": [{"filename": "src/cortex/session.py"}],
            }
        ),
    )

    source_object = result.source_objects[0]

    assert source_object.object_type == "github_pull_request"
    assert source_object.metadata_json["repo_name_hash"] != "private/cortex"
    assert source_object.metadata_json["changed_file_paths"] == [
        "src/cortex/session.py"
    ]
    assert "Implements the Linear task" in (source_object.content_text or "")
    assert "body" not in source_object.metadata_json


def test_repo_docs_payload_normalizes_docs_content_and_stale_state() -> None:
    result = normalize_repo_doc_payload(
        raw_event("repo_docs"),
        canonical_json_bytes(
            {
                "repo_id": "repo_1",
                "path": "docs/architecture/session.md",
                "title": "Session Architecture",
                "content": "Redis is the session source of truth.",
                "is_stale": True,
                "ref": "main",
            }
        ),
    )

    source_object = result.source_objects[0]

    assert source_object.object_type == "repo_doc"
    assert (
        source_object.external_object_key == "doc:repo_1:docs/architecture/session.md"
    )
    assert source_object.metadata_json["path"] == "docs/architecture/session.md"
    assert "content" not in source_object.metadata_json
    assert source_object.status == "stale"


def test_registry_uses_provider_normalizers() -> None:
    registry = NormalizerRegistry()

    assert registry.resolve(raw_event("linear")).__name__ == "normalize_linear_payload"
    assert registry.resolve(raw_event("github")).__name__ == "normalize_github_payload"
    assert (
        registry.resolve(raw_event("repo_docs")).__name__
        == "normalize_repo_doc_payload"
    )
