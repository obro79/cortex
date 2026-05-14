from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class LinearRateLimitError(Exception):
    pass


class LinearPermanentError(Exception):
    pass


@dataclass(frozen=True)
class LinearIssuesPage:
    issues: list[dict[str, Any]]
    next_cursor: str | None = None


class LinearClient(Protocol):
    async def list_issues(
        self,
        *,
        api_token: str,
        team_or_project_id: str | None = None,
        cursor: str | None = None,
        limit: int = 25,
    ) -> LinearIssuesPage: ...

    async def team_members(self, *, api_token: str, team_id: str) -> list[str]: ...


class EmptyLinearClient:
    async def list_issues(
        self,
        *,
        api_token: str,
        team_or_project_id: str | None = None,
        cursor: str | None = None,
        limit: int = 25,
    ) -> LinearIssuesPage:
        return LinearIssuesPage(issues=[], next_cursor=None)

    async def team_members(self, *, api_token: str, team_id: str) -> list[str]:
        return []


class LinearGraphQLClient:
    def __init__(
        self,
        *,
        endpoint: str = "https://api.linear.app/graphql",
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self.client = client

    async def execute(
        self,
        *,
        api_token: str,
        query: str,
        variables: dict[str, object],
    ) -> dict[str, Any]:
        headers = {
            "Authorization": api_token,
            "Content-Type": "application/json",
        }
        payload = {"query": query, "variables": variables}
        if self.client is not None:
            response = await self.client.post(
                self.endpoint, json=payload, headers=headers
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint, json=payload, headers=headers
                )
        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code == 429:
            raise LinearRateLimitError("linear_rate_limited")
        if response.status_code >= 500:
            raise LinearRateLimitError("linear_transient_error")
        if response.status_code >= 400:
            raise LinearPermanentError("linear_http_error")
        payload = response.json()
        if not isinstance(payload, dict):
            raise LinearPermanentError("linear_invalid_response")
        errors = payload.get("errors")
        if errors:
            text = str(errors)
            if "RATELIMITED" in text:
                raise LinearRateLimitError("linear_rate_limited")
            raise LinearPermanentError("linear_graphql_error")
        return payload


class RealLinearClient:
    def __init__(self, graphql: LinearGraphQLClient | None = None) -> None:
        self.graphql = graphql or LinearGraphQLClient()

    async def list_issues(
        self,
        *,
        api_token: str,
        team_or_project_id: str | None = None,
        cursor: str | None = None,
        limit: int = 25,
    ) -> LinearIssuesPage:
        payload = await self.graphql.execute(
            api_token=api_token,
            query=ISSUES_QUERY,
            variables={
                "first": limit,
                "after": cursor,
                "filter": _issue_filter(team_or_project_id),
            },
        )
        issues = payload.get("data", {}).get("issues", {}).get("nodes", [])
        page_info = payload.get("data", {}).get("issues", {}).get("pageInfo", {})
        if not isinstance(issues, list) or not isinstance(page_info, dict):
            raise LinearPermanentError("linear_invalid_issues_page")
        next_cursor = (
            page_info.get("endCursor") if page_info.get("hasNextPage") else None
        )
        return LinearIssuesPage(
            issues=[dict(issue) for issue in issues if isinstance(issue, dict)],
            next_cursor=str(next_cursor) if next_cursor else None,
        )

    async def team_members(self, *, api_token: str, team_id: str) -> list[str]:
        payload = await self.graphql.execute(
            api_token=api_token,
            query=TEAM_MEMBERS_QUERY,
            variables={"teamId": team_id},
        )
        users = (
            payload.get("data", {}).get("team", {}).get("members", {}).get("nodes", [])
        )
        if not isinstance(users, list):
            raise LinearPermanentError("linear_invalid_team_members")
        members: list[str] = []
        for user in users:
            if not isinstance(user, dict):
                continue
            external_id = user.get("id") or user.get("email")
            if external_id:
                members.append(str(external_id))
        return members


def _issue_filter(team_or_project_id: str | None) -> dict[str, object] | None:
    if not team_or_project_id:
        return None
    return {
        "or": [
            {"team": {"id": {"eq": team_or_project_id}}},
            {"project": {"id": {"eq": team_or_project_id}}},
        ]
    }


ISSUES_QUERY = """
query CortexIssues($first: Int!, $after: String, $filter: IssueFilter) {
  issues(first: $first, after: $after, filter: $filter) {
    nodes {
      id
      identifier
      title
      description
      url
      createdAt
      updatedAt
      team { id name }
      project { id name }
      state { id name }
      assignee { id name }
      creator { id name }
      labels { nodes { id name } }
      comments(first: 10) { nodes { id body createdAt updatedAt } }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

TEAM_MEMBERS_QUERY = """
query CortexTeamMembers($teamId: String!) {
  team(id: $teamId) {
    members {
      nodes {
        id
        email
      }
    }
  }
}
"""
