from __future__ import annotations

import hashlib
import hmac
import json

from cortex.connectors.github.service import GitHubConnectorServices
from cortex.connectors.linear.client import LinearIssuesPage
from cortex.connectors.linear.service import LinearConnectorServices
from cortex.connectors.repo_docs.service import RepoDocsConnectorServices
from cortex.platform import (
    InMemoryEphemeralCache,
    RateLimitPolicy,
    RateLimitService,
)


class RecordingLinearClient:
    def __init__(self) -> None:
        self.call_count = 0

    async def list_issues(
        self,
        *,
        api_token: str,
        team_or_project_id: str | None = None,
        cursor: str | None = None,
        limit: int = 25,
    ) -> LinearIssuesPage:
        self.call_count += 1
        return LinearIssuesPage(issues=[])


async def test_linear_backfill_respects_selected_team_or_project() -> None:
    services = LinearConnectorServices(api_token_configured=True)
    services.select_sources(
        workspace_id="ws_1", sources=[{"id": "proj_1", "type": "project"}]
    )

    result = await services.backfill(
        workspace_id="ws_1",
        source_connection_id="src_linear",
        issues=[
            {
                "id": "1",
                "identifier": "COR-123",
                "title": "Allowed",
                "project": {"id": "proj_1"},
            },
            {
                "id": "2",
                "identifier": "COR-999",
                "title": "Hidden",
                "project": {"id": "proj_2"},
            },
        ],
    )

    assert result["raw_events_created"] == 1
    assert services.health("ws_1")["auth_status"] == "active"


async def test_linear_live_backfill_enforces_provider_rate_limit() -> None:
    client = RecordingLinearClient()
    services = LinearConnectorServices(
        api_token_configured=True,
        api_token="token",
        client=client,
        provider_rate_limiter=RateLimitService(InMemoryEphemeralCache()),
        provider_rate_limit_policy=RateLimitPolicy(
            name="provider", limit=1, window_seconds=60, namespace="provider"
        ),
    )

    first = await services.live_backfill(
        workspace_id="ws_1", source_connection_id="src_linear"
    )
    second = await services.live_backfill(
        workspace_id="ws_1", source_connection_id="src_linear"
    )

    assert first["ok"] is True
    assert second == {
        "ok": False,
        "error": "rate_limited",
        "retry_after_seconds": 60,
    }
    assert client.call_count == 1


async def test_github_backfill_respects_selected_repo() -> None:
    services = GitHubConnectorServices(app_configured=True)
    services.select_repos(workspace_id="ws_1", repos=[{"id": "44"}])

    result = await services.backfill(
        workspace_id="ws_1",
        source_connection_id="src_github",
        events=[
            {
                "repository": {"id": 44},
                "pull_request": {"id": 1, "number": 12, "title": "Allowed"},
            },
            {
                "repository": {"id": 55},
                "issue": {"id": 2, "number": 13, "title": "Hidden"},
            },
        ],
    )

    assert result["raw_events_created"] == 1
    assert services.health("ws_1")["auth_status"] == "active"


async def test_github_webhook_verifies_signature_and_persists_json_payload() -> None:
    services = GitHubConnectorServices(app_configured=True, webhook_secret="secret")
    body = json.dumps(
        {
            "repository": {"id": 44},
            "pull_request": {"id": 1, "number": 12, "title": "Allowed"},
        },
        separators=(",", ":"),
    ).encode()
    signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()

    result = await services.webhook(
        workspace_id="ws_1",
        source_connection_id="src_github",
        body=body,
        signature=signature,
        event_name="pull_request",
        delivery_id="delivery_1",
    )

    raw_event = services.raw_events.get_by_idempotency_key(
        "ws_1", "github:ws_1:delivery:delivery_1"
    )
    assert result["raw_event_created"] is True
    assert raw_event is not None
    assert raw_event.payload_ref is not None
    assert services.payload_store.get(raw_event.payload_ref).startswith(b"{")


async def test_github_webhook_ignores_unselected_repository() -> None:
    services = GitHubConnectorServices(app_configured=True, webhook_secret="secret")
    services.select_repos(workspace_id="ws_1", repos=[{"id": "44"}])
    body = json.dumps(
        {
            "repository": {"id": 55},
            "pull_request": {"id": 1, "number": 12, "title": "Hidden"},
        },
        separators=(",", ":"),
    ).encode()
    signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()

    result = await services.webhook(
        workspace_id="ws_1",
        source_connection_id="src_github",
        body=body,
        signature=signature,
        event_name="pull_request",
        delivery_id="delivery_unselected",
    )

    assert result == {"ok": True, "status": "ignored_unselected"}
    assert (
        services.raw_events.get_by_idempotency_key(
            "ws_1", "github:ws_1:delivery:delivery_unselected"
        )
        is None
    )


async def test_github_webhook_enforces_source_connection_binding() -> None:
    services = GitHubConnectorServices(app_configured=True, webhook_secret="secret")
    services.select_repos(
        workspace_id="ws_1",
        repos=[{"id": "44", "source_connection_id": "src_repo_44"}],
    )
    body = json.dumps(
        {
            "repository": {"id": 44},
            "pull_request": {"id": 1, "number": 12, "title": "Allowed"},
        },
        separators=(",", ":"),
    ).encode()
    signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()

    result = await services.webhook(
        workspace_id="ws_1",
        source_connection_id="src_wrong",
        body=body,
        signature=signature,
        event_name="pull_request",
        delivery_id="delivery_wrong_source",
    )

    assert result == {"ok": True, "status": "ignored_source_mismatch"}
    assert (
        services.raw_events.get_by_idempotency_key(
            "ws_1", "github:ws_1:delivery:delivery_wrong_source"
        )
        is None
    )


async def test_github_webhook_rejects_when_secret_is_not_configured() -> None:
    services = GitHubConnectorServices(app_configured=True)
    body = json.dumps({"repository": {"id": 44}}, separators=(",", ":")).encode()

    result = await services.webhook(
        workspace_id="ws_1",
        source_connection_id="src_github",
        body=body,
        signature="",
        event_name="pull_request",
        delivery_id="delivery_1",
    )

    assert result == {"ok": False, "status": "invalid_signature"}


async def test_repo_docs_import_hashes_and_skips_unchanged_docs() -> None:
    services = RepoDocsConnectorServices()
    services.select_roots(workspace_id="ws_1", roots=[{"path": "docs"}])

    first = await services.import_docs(
        workspace_id="ws_1",
        source_connection_id="src_docs",
        docs=[
            {
                "repo_id": "repo_1",
                "path": "docs/session.md",
                "content": "Session docs",
            },
            {
                "repo_id": "repo_1",
                "path": "src/private.py",
                "content": "Not allowed",
            },
        ],
    )
    second = await services.import_docs(
        workspace_id="ws_1",
        source_connection_id="src_docs",
        docs=[
            {"repo_id": "repo_1", "path": "docs/session.md", "content": "Session docs"}
        ],
    )

    assert first["raw_events_created"] == 1
    assert second["unchanged_skipped"] == 1
    assert services.health("ws_1")["imported_doc_count"] == 1
