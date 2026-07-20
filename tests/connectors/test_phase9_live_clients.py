from __future__ import annotations

import json

import httpx

from cortex.connectors.github.client import GitHubHttpClient, RealGitHubClient
from cortex.connectors.github.service import GitHubConnectorServices
from cortex.connectors.linear.client import LinearGraphQLClient, RealLinearClient
from cortex.connectors.linear.service import LinearConnectorServices


async def test_real_linear_client_uses_api_token_and_maps_issue_page() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "data": {
                    "issues": {
                        "nodes": [
                            {
                                "id": "lin_1",
                                "identifier": "COR-123",
                                "title": "Live Linear issue",
                                "comments": {"nodes": [{"id": "c1", "body": "note"}]},
                                "labels": {"nodes": [{"id": "label_1"}]},
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        linear = RealLinearClient(LinearGraphQLClient(client=client))
        page = await linear.list_issues(
            api_token="lin_api_key",
            team_or_project_id="proj_1",
            limit=5,
        )

    assert seen["authorization"] == "lin_api_key"
    assert page.issues[0]["identifier"] == "COR-123"
    assert page.next_cursor is None
    assert seen["body"]["variables"]["first"] == 5


async def test_linear_live_backfill_persists_fetched_issue() -> None:
    class FakeLinearClient:
        async def list_issues(self, **_kwargs: object):
            return type(
                "Page",
                (),
                {
                    "issues": [
                        {
                            "id": "lin_1",
                            "identifier": "COR-123",
                            "title": "Live Linear issue",
                            "team": {"id": "team_1"},
                            "comments": {"nodes": [{"body": "comment"}]},
                            "labels": {"nodes": [{"id": "label_1"}]},
                        }
                    ]
                },
            )()

    services = LinearConnectorServices(
        api_token_configured=True,
        api_token="lin_api_key",
        client=FakeLinearClient(),
    )

    result = await services.live_backfill(
        workspace_id="ws_1",
        source_connection_id="src_linear",
    )

    assert result["fetched"] == 1
    assert result["raw_events_created"] == 1


async def test_real_github_client_uses_bearer_token_and_backfills_repo() -> None:
    seen_paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer gh_installation_token"
        seen_paths.append(request.url.path)
        if request.url.path.endswith("/pulls"):
            return httpx.Response(
                200,
                json=[{"id": 1, "number": 12, "title": "Live PR"}],
            )
        if request.url.path.endswith("/issues"):
            return httpx.Response(
                200,
                json=[{"id": 2, "number": 13, "title": "Live issue"}],
            )
        if request.url.path.endswith("/commits"):
            return httpx.Response(
                200,
                json=[
                    {
                        "sha": "abc1234",
                        "html_url": "https://github.com/acme/cortex/commit/abc1234",
                        "commit": {
                            "message": "Live commit",
                            "author": {"date": "2026-05-08T00:00:00Z"},
                        },
                    }
                ],
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        github = RealGitHubClient(GitHubHttpClient(client=client))
        backfill = await github.backfill_repository(
            access_token="gh_installation_token",
            owner="acme",
            repo="cortex",
            limit=3,
        )

    assert seen_paths == [
        "/repos/acme/cortex/pulls",
        "/repos/acme/cortex/issues",
        "/repos/acme/cortex/commits",
    ]
    assert [event.keys() for event in backfill.events] == [
        {"repository", "pull_request"},
        {"repository", "issue"},
        {"repository", "commit"},
    ]


async def test_github_live_backfill_persists_fetched_events() -> None:
    class FakeGitHubClient:
        async def backfill_repository(self, **_kwargs: object):
            return type(
                "Backfill",
                (),
                {
                    "events": [
                        {
                            "repository": {"id": 44},
                            "pull_request": {
                                "id": 1,
                                "number": 12,
                                "title": "Live PR",
                            },
                        }
                    ]
                },
            )()

    services = GitHubConnectorServices(
        app_configured=True,
        installation_token="gh_installation_token",
        client=FakeGitHubClient(),
    )
    services.select_repos(
        workspace_id="ws_1",
        repos=[{"id": "44", "source_connection_id": "src_github"}],
    )

    result = await services.live_backfill(
        workspace_id="ws_1",
        source_connection_id="src_github",
        owner="acme",
        repo="cortex",
    )

    assert result["fetched"] == 1
    assert result["raw_events_created"] == 1
    assert result["provenance"] == "live"
    assert services.health("ws_1")["sync_sources"] == [
        {
            "source_connection_id": "src_github",
            "status": "completed",
            "cursor": "pull_request:1",
            "last_error": None,
            "provenance": "live",
        }
    ]
