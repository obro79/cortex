"""Run a deterministic, credential-free GitHub snapshot import preflight."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from cortex.connectors.github import (
    GitHubImportPlan,
    GitHubSnapshotEvent,
    GitHubSnapshotPage,
    GitHubSnapshotPageInput,
)
from cortex.ingestion.raw_events import RawEventInput

FIXTURE_CLASSIFICATION = "fixture-only; no live GitHub API calls"
LIVE_PREREQUISITES = (
    "A GitHub App installed on the target repositories",
    "An installation access token supplied only to the live connector runtime",
    "Selected repository/source-connection bindings",
)


class RecordingIngestion:
    def __init__(self) -> None:
        self.items: list[RawEventInput] = []

    async def ingest(self, item: RawEventInput) -> str:
        self.items.append(item)
        return "accepted"


async def build_report() -> dict[str, Any]:
    """Exercise one supplied fixture page without reading environment variables."""
    fixture_event = GitHubSnapshotEvent.from_provider_event(
        {
            "repository": {"id": "fixture-repo-44", "full_name": "acme/cortex"},
            "pull_request": {
                "id": "fixture-pr-12",
                "number": 12,
                "title": "Fixture-only snapshot readiness",
                "updated_at": "2026-07-19T12:00:00Z",
            },
        }
    )
    plan = GitHubImportPlan(
        workspace_id="fixture-workspace",
        source_connection_id="fixture-github-source",
        snapshot=GitHubSnapshotPage(
            GitHubSnapshotPageInput(repository_ids=("fixture-repo-44",), page_size=1),
            (fixture_event,),
        ),
    )
    ingestion = RecordingIngestion()
    execution = await plan.execute(ingestion)
    return {
        "classification": FIXTURE_CLASSIFICATION,
        "live_api_calls": False,
        "reads_environment_credentials": False,
        "submitted": execution.submitted,
        "event_types": [item.event_type for item in ingestion.items],
        "checkpoint": "complete" if execution.next_page_input is None else "pending",
        "live_prerequisites": list(LIVE_PREREQUISITES),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser.parse_args()


def render_human(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "GitHub snapshot preflight: PASS",
            f"Classification: {report['classification']}",
            "Fixture result: "
            f"submitted={report['submitted']} event_types={report['event_types']} ",
            f"checkpoint={report['checkpoint']}",
            "Live prerequisite (not exercised): " + "; ".join(LIVE_PREREQUISITES),
        ]
    )


async def main() -> int:
    args = parse_args()
    report = await build_report()
    if args.format == "json":
        print(json.dumps(report, sort_keys=True))
    else:
        print(render_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
