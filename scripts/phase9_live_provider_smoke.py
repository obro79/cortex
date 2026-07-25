from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime

from cortex.connectors.github.client import RealGitHubClient
from cortex.connectors.github.service import GitHubConnectorServices
from cortex.connectors.linear.client import RealLinearClient
from cortex.connectors.linear.service import LinearConnectorServices

WORKSPACE_ID = f"ws_phase9_live_{int(datetime.now(UTC).timestamp())}"


async def main() -> int:
    result: dict[str, object] = {"workspace_id": WORKSPACE_ID}
    linear_token = os.getenv("LINEAR_API_TOKEN", "")
    github_token = os.getenv("GITHUB_INSTALLATION_TOKEN", "") or os.getenv(
        "GITHUB_TOKEN", ""
    )
    github_repo = os.getenv("GITHUB_REPOSITORY", "")

    if linear_token:
        linear = LinearConnectorServices(
            api_token_configured=True,
            api_token=linear_token,
            client=RealLinearClient(),
        )
        result["linear"] = await linear.live_backfill(
            workspace_id=WORKSPACE_ID,
            source_connection_id="src_phase9_linear_live",
            limit=int(os.getenv("PHASE9_LIVE_LIMIT", "5")),
        )
    else:
        result["linear"] = {"ok": False, "skipped": "LINEAR_API_TOKEN not set"}

    if github_token and "/" in github_repo:
        owner, repo = github_repo.split("/", 1)
        github = GitHubConnectorServices(
            app_configured=True,
            installation_token=github_token,
            client=RealGitHubClient(),
        )
        result["github"] = await github.live_backfill(
            workspace_id=WORKSPACE_ID,
            source_connection_id="src_phase9_github_live",
            owner=owner,
            repo=repo,
            limit=int(os.getenv("PHASE9_LIVE_LIMIT", "5")),
        )
    else:
        result["github"] = {
            "ok": False,
            "skipped": (
                "GITHUB_INSTALLATION_TOKEN/GITHUB_TOKEN and GITHUB_REPOSITORY required"
            ),
        }

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
