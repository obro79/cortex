from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from cortex.dev.workbench import DevWorkbenchService

DEFAULT_QUERY = "COR-123 session migration constraints"
FIXTURE_PROVENANCE = (
    "Synthetic deterministic COR-123 fixture corpus; no live provider data. "
    "Media records are fixtures and explicitly not live OCR or transcription."
)


async def build_rehearsal_report(query: str = DEFAULT_QUERY) -> dict[str, Any]:
    """Seed, run, and query the local demo without exposing source text or URLs."""
    service = DevWorkbenchService()
    seeded = service.seed()
    run = await service.run_pipeline()
    result = service.query(query)

    fixture_to_provider = {
        source_object.metadata_json["fixture_id"]: source_object.provider
        for source_object in service.repository.source_objects.values()
    }
    ranked_sources = [
        {
            "rank": candidate["rank"],
            "fixture_id": candidate["fixture_id"],
            "provider": fixture_to_provider[candidate["fixture_id"]],
        }
        for candidate in result["final_ranking"]
    ]
    return {
        "provenance": FIXTURE_PROVENANCE,
        "workspace_id": seeded["workspace_id"],
        "corpus": {
            "source_object_count": seeded["counts"]["source_objects"],
            "source_file_count": seeded["counts"]["source_files"],
            "provider_counts": seeded["provider_counts"],
            "media_counts": seeded["media_counts"],
        },
        "pipeline": {
            "run_id": run["run_id"],
            "status": run["status"],
            "stage_count": len(run["stages"]),
        },
        "query": {
            "issue": "COR-123",
            "gate_status": result["gate_status"],
            "ranked_sources": ranked_sources,
        },
    }


def render_human(report: dict[str, Any]) -> str:
    corpus = report["corpus"]
    pipeline = report["pipeline"]
    query = report["query"]
    ranked_sources = ", ".join(
        f"#{source['rank']} {source['fixture_id']} ({source['provider']})"
        for source in query["ranked_sources"]
    )
    return "\n".join(
        [
            "Cortex hackathon demo rehearsal",
            f"Provenance: {report['provenance']}",
            (
                "Corpus: "
                f"{corpus['source_object_count']} source objects, "
                f"{corpus['source_file_count']} fixture media files; "
                f"providers={corpus['provider_counts']}; media={corpus['media_counts']}"
            ),
            (
                "Pipeline: "
                f"{pipeline['run_id']} {pipeline['status']} "
                f"({pipeline['stage_count']} stages)"
            ),
            f"COR-123 gate: {query['gate_status']}",
            f"Ranked fixture sources: {ranked_sources}",
        ]
    )


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rehearse the deterministic COR-123 demo."
    )
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)
    report = await build_rehearsal_report(args.query)
    if args.format == "json":
        print(json.dumps(report, sort_keys=True))
    else:
        print(render_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
