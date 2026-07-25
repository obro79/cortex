from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cortex.contracts.enums import ContextGateStatus, EvidencePackStatus

from .fixtures import WORKSPACE_ID, FixtureRepository

EVIDENCE_PACK_ID = "ep-cor-123"
GATE_RESULT_ID = "gate-cor-123"
RETRIEVAL_REQUEST_ID = "rr-cor-123"


def build_evidence_pack(repository: FixtureRepository) -> dict[str, Any]:
    citations = [
        {
            "citation_id": f"cite-{chunk.metadata_json['fixture_id']}",
            "source_object_id": chunk.source_object_id,
            "source_file_id": chunk.source_file_id,
            "source_chunk_id": chunk.id,
            "label": chunk.citation_label,
            "url": chunk.citation_url,
            "source_kind": chunk.metadata_json["source_kind"],
            "is_stale": chunk.metadata_json["is_stale"],
        }
        for chunk in repository.source_chunks.values()
    ]
    provider_coverage = {
        provider: True
        for provider in sorted(
            {
                source_object.provider
                for source_object in repository.source_objects.values()
            }
        )
    }
    media_coverage = {
        str(source_file.metadata_json["media_kind"]): True
        for source_file in repository.source_files.values()
    }
    return {
        "id": EVIDENCE_PACK_ID,
        "workspace_id": WORKSPACE_ID,
        "retrieval_request_id": RETRIEVAL_REQUEST_ID,
        "status": EvidencePackStatus.CREATED.value,
        "claims": [
            {
                "claim": "Postgres is the approved session source of truth.",
                "citation_ids": [
                    "cite-slack-thread-sessions-postgres",
                    "cite-slack-huddle-session-rollout-caption",
                    "cite-gdrive-session-migration-brief",
                ],
            },
            {
                "claim": (
                    "Redis documentation is stale and conflicts with newer "
                    "implementation evidence."
                ),
                "citation_ids": ["cite-repo-doc-session-storage", "cite-github-pr-184"],
            },
        ],
        "citations": citations,
        "source_coverage": provider_coverage,
        "media_coverage": media_coverage,
        "permission_exclusions": [],
        "missing_context": [],
        "stale_evidence": ["repo-doc-session-storage"],
        "conflicting_evidence": [
            {
                "stale_source": "repo-doc-session-storage",
                "newer_sources": [
                    "slack-thread-sessions-postgres",
                    "github-pr-184",
                    "linear-issue-COR-123",
                ],
                "summary": (
                    "Stale docs say Redis is authoritative while newer sources "
                    "require Postgres sessions."
                ),
            }
        ],
        "token_budget": 4000,
        "gate_result": build_gate_result(),
        "created_at": datetime.now(UTC).isoformat(),
    }


def build_gate_result() -> dict[str, Any]:
    return {
        "id": GATE_RESULT_ID,
        "workspace_id": WORKSPACE_ID,
        "retrieval_request_id": RETRIEVAL_REQUEST_ID,
        "evidence_pack_id": EVIDENCE_PACK_ID,
        "status": ContextGateStatus.BLOCK.value,
        "risk_category": "architecture_conflict",
        "reasons": [
            (
                "COR-123 touches session storage while repo docs conflict with "
                "newer Postgres session decisions."
            ),
            (
                "Middleware fallback blocker COR-119 must be resolved or "
                "explicitly accepted."
            ),
        ],
        "required_actions": [
            "Confirm whether Redis read fallback remains during rollout.",
            (
                "Update stale session storage docs before implementation is "
                "treated as safe."
            ),
        ],
        "gate_version": "fixture-gate-v1",
    }
