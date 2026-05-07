from cortex.chunking.config import load_retrieval_config
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.retrieval.candidates import Candidate
from cortex.retrieval.permissions import PermissionFilter
from cortex.retrieval.query import QueryPlanner


def test_permission_filter_excludes_non_allowlisted_without_leaking_ids(
    phase4_source_object,
) -> None:
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(phase4_source_object)[0]
    plan = QueryPlanner().plan(query="session", source_allowlist=["other_source"])

    allowed, summary = PermissionFilter().filter([Candidate(chunk)], plan)

    assert allowed == []
    assert summary == {"excluded_count": 1, "reason": "source_allowlist"}
