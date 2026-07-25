from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.retrieval.candidates import Candidate
from cortex.retrieval.evidence import EvidencePackBuilder
from cortex.retrieval.service import RetrievalServiceResponse
from cortex.retrieval.task_context import TaskContextRequest, TaskContextService


def _response(*, errors: dict[str, str] | None = None) -> RetrievalServiceResponse:
    now = datetime.now(UTC).isoformat()
    return RetrievalServiceResponse(
        ok=True,
        retrieval_request_id="rr_1",
        evidence_pack_id="ep_1",
        text="unused",
        evidence_pack={
            "citations_json": {
                "items": [
                    {
                        "source_chunk_id": "cite_1",
                        "source_object_id": "so_1",
                        "citation_label": "Decision",
                        "snippet": "Postgres remains canonical.",
                        "provider": "slack",
                        "source_type": "slack_thread",
                        "last_synced_at": now,
                        "source_updated_at": now,
                        "retrieval_paths": ["fts"],
                        "score_provenance": {"lexical": 0.9},
                        "content_hash": "sha256:abc",
                        "source_version": "v1",
                    }
                ]
            },
            "candidate_summary_json": {
                "errors": errors or {},
                "lexical_candidate_count": 1,
                "vector_candidate_count": 0,
                "versions": {"ranker": "r1"},
            },
            "missing_context_json": {},
            "conflict_summary_json": {},
        },
        status="completed",
        latency_ms=1,
    )


def test_task_context_is_evidence_only_and_projects_vector_outage_as_partial() -> None:
    request = TaskContextRequest.model_validate(
        {"task": {"objective": "Implement COR-123"}}
    )

    result = (
        TaskContextService()
        .project(
            request=request,
            response=_response(errors={"vector": "ConnectionError"}),
            trace_id="trace_1",
            live_data=True,
        )
        .model_dump(mode="json")
    )

    assert result["status"] == "partial"
    assert result["task_context"]["retrieval"]["status"] == "fts_only"
    assert result["task_context"]["evidence_items"][0]["provider"] == "slack"
    assert "answer" not in result
    assert "recommendation" not in result


def test_freshness_requirement_never_relaxes_to_stale_evidence() -> None:
    stale = _response()
    citation = stale.evidence_pack["citations_json"]["items"][0]
    assert isinstance(citation, dict)
    citation["last_synced_at"] = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    request = TaskContextRequest.model_validate(
        {
            "task": {"objective": "Implement COR-123"},
            "freshness": {"maximum_age_seconds": 60, "require_fresh": True},
        }
    )

    result = TaskContextService().project(
        request=request, response=stale, trace_id="trace_1", live_data=True
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == "FRESHNESS_REQUIREMENT_UNMET"


def test_task_context_enforces_a_total_not_per_citation_token_budget() -> None:
    response = _response()
    citations = response.evidence_pack["citations_json"]["items"]
    assert isinstance(citations, list)
    citations.extend(
        [
            {
                **citations[0],
                "source_chunk_id": f"cite_{index}",
                "snippet": "one two three",
            }
            for index in range(2, 5)
        ]
    )
    request = TaskContextRequest.model_validate(
        {
            "task": {"objective": "Implement COR-123"},
            "budget": {"maximum_evidence_items": 12, "maximum_tokens": 1},
        }
    )

    result = TaskContextService().project(
        request=request,
        response=response,
        trace_id="trace_1",
        live_data=True,
    )

    assert result.task_context is not None
    snippets = [item.snippet for item in result.task_context.evidence_items]
    assert sum(len(snippet.split()) for snippet in snippets) <= 1


def test_chunk_timestamps_flow_into_fresh_task_context(
    phase4_source_object,
) -> None:
    now = datetime.now(UTC)
    source = phase4_source_object.model_copy(
        update={
            "content_text": "COR-123 keeps the source timestamps intact.",
            "source_updated_at": now,
            "updated_at": now,
        }
    )
    chunker = SourceAwareChunker(load_retrieval_config().chunking)
    chunk = chunker.chunks_for_source_object(source)[0]
    payloads = EvidencePackBuilder().build_payloads(
        candidates=[Candidate(source_chunk=chunk, lexical_score=1, paths={"fts"})],
        permission_exclusions={"excluded_count": 0},
        token_budget=100,
        versions={"final_evidence_limit": "12"},
    )
    response = RetrievalServiceResponse(
        ok=True,
        retrieval_request_id="rr_1",
        evidence_pack_id="ep_1",
        text="unused",
        evidence_pack=payloads,
        status="completed",
        latency_ms=1,
    )
    request = TaskContextRequest.model_validate(
        {
            "task": {"objective": "Implement COR-123"},
            "freshness": {"maximum_age_seconds": 60, "require_fresh": True},
        }
    )

    result = TaskContextService().project(
        request=request,
        response=response,
        trace_id="trace_1",
        live_data=True,
    )

    assert result.ok is True
    assert result.task_context is not None
    evidence = result.task_context.evidence_items[0]
    assert evidence.freshness == "fresh"
    assert evidence.source_updated_at == now.isoformat()
    assert evidence.last_synced_at == now.isoformat()
