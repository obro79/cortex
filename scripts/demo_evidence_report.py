"""Render the fixture-safe Cortex demo evidence control-plane report."""

from __future__ import annotations

import argparse
import asyncio
import json

from cortex.demo import DemoEvidenceControlPlane, DemoEvidenceReport


def render_human(report: DemoEvidenceReport) -> str:
    """Render audience-facing counts and statuses without source material."""
    return "\n".join(
        (
            "Cortex demo evidence control plane",
            f"Disclosure: {report.disclosure}",
            (
                "Corpus: "
                f"{report.corpus.source_object_count} source objects; "
                f"{report.corpus.source_file_count} media files; "
                f"providers={report.corpus.provider_counts}; "
                f"media={report.corpus.media_counts}"
            ),
            (
                "Pipeline: "
                f"{report.pipeline.status}; {report.pipeline.stage_count} stages; "
                f"statuses={report.pipeline.stage_status_counts}"
            ),
            (
                "Decision: "
                f"query={report.decision.query_status}; "
                f"evidence={report.decision.evidence_status}; "
                f"gate={report.decision.gate_status}; "
                f"handoff={report.decision.handoff_status}"
            ),
            "Incremental ingest: "
            + ", ".join(
                f"t+{step.offset_seconds}s {step.stage}:{step.status}"
                for step in report.incremental_ingest_timeline
            ),
        )
    )


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render fixture-safe audience evidence for the Cortex demo."
    )
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    report = await DemoEvidenceControlPlane().build_report()
    if args.format == "json":
        print(json.dumps(report.as_dict(), sort_keys=True))
    else:
        print(render_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
