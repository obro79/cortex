from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

GitHubQueryParams = dict[str, str | int | float | bool | None]


class GitHubRateLimitError(Exception):
    pass


class GitHubPermanentError(Exception):
    pass


@dataclass(frozen=True)
class GitHubRepoPage:
    repos: list[dict[str, Any]]


@dataclass(frozen=True)
class GitHubRepoBackfill:
    events: list[dict[str, Any]]


class GitHubClient(Protocol):
    async def list_installation_repositories(
        self, *, access_token: str
    ) -> GitHubRepoPage: ...

    async def backfill_repository(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
        limit: int = 25,
    ) -> GitHubRepoBackfill: ...


class EmptyGitHubClient:
    async def list_installation_repositories(
        self, *, access_token: str
    ) -> GitHubRepoPage:
        return GitHubRepoPage(repos=[])

    async def backfill_repository(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
        limit: int = 25,
    ) -> GitHubRepoBackfill:
        return GitHubRepoBackfill(events=[])


class GitHubHttpClient:
    def __init__(
        self,
        *,
        base_url: str = "https://api.github.com",
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = client

    async def get(
        self,
        path: str,
        *,
        access_token: str,
        params: GitHubQueryParams | None = None,
    ) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.client is not None:
            response = await self.client.get(
                f"{self.base_url}{path}", headers=headers, params=params
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}{path}", headers=headers, params=params
                )
        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> Any:
        if (
            response.status_code in {403, 429}
            and response.headers.get("x-ratelimit-remaining") == "0"
        ):
            raise GitHubRateLimitError("github_rate_limited")
        if response.status_code >= 500:
            raise GitHubRateLimitError("github_transient_error")
        if response.status_code >= 400:
            raise GitHubPermanentError("github_http_error")
        if response.content:
            return response.json()
        return {}


class RealGitHubClient:
    def __init__(self, http: GitHubHttpClient | None = None) -> None:
        self.http = http or GitHubHttpClient()

    async def list_installation_repositories(
        self, *, access_token: str
    ) -> GitHubRepoPage:
        payload = await self.http.get(
            "/installation/repositories",
            access_token=access_token,
            params={"per_page": 100},
        )
        repos = payload.get("repositories", []) if isinstance(payload, dict) else []
        if not isinstance(repos, list):
            raise GitHubPermanentError("github_invalid_repositories")
        return GitHubRepoPage(
            repos=[dict(repo) for repo in repos if isinstance(repo, dict)]
        )

    async def backfill_repository(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
        limit: int = 25,
    ) -> GitHubRepoBackfill:
        pulls = await self.http.get(
            f"/repos/{owner}/{repo}/pulls",
            access_token=access_token,
            params={"state": "all", "per_page": limit},
        )
        issues = await self.http.get(
            f"/repos/{owner}/{repo}/issues",
            access_token=access_token,
            params={"state": "all", "per_page": limit},
        )
        commits = await self.http.get(
            f"/repos/{owner}/{repo}/commits",
            access_token=access_token,
            params={"per_page": limit},
        )
        events: list[dict[str, Any]] = []
        repo_payload = {"id": f"{owner}/{repo}", "full_name": f"{owner}/{repo}"}
        for pull in pulls if isinstance(pulls, list) else []:
            if isinstance(pull, dict):
                events.append({"repository": repo_payload, "pull_request": pull})
        for issue in issues if isinstance(issues, list) else []:
            if isinstance(issue, dict) and "pull_request" not in issue:
                events.append({"repository": repo_payload, "issue": issue})
        for commit in commits if isinstance(commits, list) else []:
            if isinstance(commit, dict):
                events.append(
                    {
                        "repository": repo_payload,
                        "commit": {
                            "sha": commit.get("sha"),
                            "message": _commit_message(commit),
                            "html_url": commit.get("html_url"),
                            "timestamp": _commit_timestamp(commit),
                            "author": commit.get("author"),
                        },
                    }
                )
        return GitHubRepoBackfill(events=events)


def _commit_message(commit: dict[str, Any]) -> str | None:
    nested = commit.get("commit")
    if isinstance(nested, dict):
        message = nested.get("message")
        return str(message) if message else None
    return None


def _commit_timestamp(commit: dict[str, Any]) -> str | None:
    nested = commit.get("commit")
    if isinstance(nested, dict):
        author = nested.get("author")
        if isinstance(author, dict) and author.get("date"):
            return str(author["date"])
    return None
