from cortex.chunking.config import load_retrieval_config
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.retrieval.candidates import Candidate
from cortex.retrieval.evidence import EvidencePackBuilder


def test_evidence_pack_builder_resolves_citations_and_snippet_budget(
    phase4_source_object,
) -> None:
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(phase4_source_object)[0]
    payloads = EvidencePackBuilder().build_payloads(
        candidates=[Candidate(chunk, lexical_score=1.0)],
        permission_exclusions={"excluded_count": 0},
        token_budget=3,
        versions={"final_evidence_limit": "12", "ranker_version": "ranking-v1"},
    )

    citation = payloads["citations_json"]["items"][0]
    assert citation["source_chunk_id"] == chunk.id
    assert len(citation["snippet"].split()) == 3
    assert payloads["source_coverage_json"]["source_object_ids"] == ["so_1"]
