"""Typed, fixture-only evidence summary for the hackathon demo."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Literal

from cortex.dev.workbench import DevWorkbenchService

DEMO_SCOPE = "COR-123"
PROVENANCE = "synthetic_deterministic_fixture_corpus"
NOT_LIVE_DISCLOSURE = (
    "Synthetic deterministic fixtures only; no live provider data, OCR, or "
    "transcription is represented."
)

SafetyStatus = Literal["fixture_only", "blocked_pending_human_review"]


@dataclass(frozen=True)
class CorpusEvidence:
    source_object_count: int
    source_file_count: int
    provider_counts: dict[str, int]
    media_counts: dict[str, int]


@dataclass(frozen=True)
class PipelineEvidence:
    status: str
    stage_count: int
    stage_status_counts: dict[str, int]


@dataclass(frozen=True)
class IncrementalIngestStep:
    offset_seconds: int
    stage: str
    status: str


@dataclass(frozen=True)
class DecisionEvidence:
    query_status: str
    evidence_status: str
    gate_status: str
    handoff_status: SafetyStatus


@dataclass(frozen=True)
class DemoEvidenceReport:
    """JSON-ready, sanitized public contract for a future demo API route."""

    scope: str
    provenance: str
    live_data: Literal[False]
    disclosure: str
    corpus: CorpusEvidence
    pipeline: PipelineEvidence
    decision: DecisionEvidence
    incremental_ingest_timeline: tuple[IncrementalIngestStep, ...]

    def as_dict(self) -> dict[str, object]:
        """Return JSON-compatible primitives without fixture source content."""
        payload = asdict(self)
        payload["incremental_ingest_timeline"] = list(
            payload["incremental_ingest_timeline"]
        )
        return payload


class DemoEvidenceControlPlane:
    """Build a deterministic audience report from the local fixture workbench."""

    async def build_report(self) -> DemoEvidenceReport:
        workbench = DevWorkbenchService()
        seeded = workbench.seed()
        run = await workbench.run_pipeline()
        query = workbench.query(DEMO_SCOPE)
        evidence_pack = workbench.get_evidence_pack(query["evidence_pack_id"])
        if evidence_pack is None:
            raise RuntimeError("Fixture evidence pack was not created.")

        counts = seeded["counts"]
        stages = run["stages"]
        stage_statuses = Counter(str(stage["status"]) for stage in stages)
        gate_status = str(query["gate_status"])
        return DemoEvidenceReport(
            scope=DEMO_SCOPE,
            provenance=PROVENANCE,
            live_data=False,
            disclosure=NOT_LIVE_DISCLOSURE,
            corpus=CorpusEvidence(
                source_object_count=int(counts["source_objects"]),
                source_file_count=int(counts["source_files"]),
                provider_counts=dict(seeded["provider_counts"]),
                media_counts=dict(seeded["media_counts"]),
            ),
            pipeline=PipelineEvidence(
                status=str(run["status"]),
                stage_count=len(stages),
                stage_status_counts=dict(sorted(stage_statuses.items())),
            ),
            decision=DecisionEvidence(
                query_status="fixture_evidence_available",
                evidence_status=str(evidence_pack["status"]),
                gate_status=gate_status,
                handoff_status=(
                    "blocked_pending_human_review"
                    if gate_status == "block"
                    else "fixture_only"
                ),
            ),
            incremental_ingest_timeline=tuple(
                IncrementalIngestStep(
                    offset_seconds=index,
                    stage=str(stage["stage"]),
                    status=str(stage["status"]),
                )
                for index, stage in enumerate(stages)
            ),
        )
