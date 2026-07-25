from cortex.chunking.config import load_retrieval_config
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.enums import SourceChunkStatus
from cortex.retrieval.candidates import Candidate
from cortex.retrieval.hybrid import HybridCandidateFuser
from cortex.retrieval.ranking import CandidateRanker


def test_vector_candidates_can_change_hybrid_ordering(phase4_source_object) -> None:
    chunker = SourceAwareChunker(load_retrieval_config().chunking)
    base = chunker.chunks_for_source_object(phase4_source_object)[0]
    lexical_chunk = base.model_copy(update={"id": "chunk_lexical"})
    vector_chunk = base.model_copy(update={"id": "chunk_vector"})

    fused = HybridCandidateFuser().fuse(
        workspace_id="ws_1",
        lexical_candidates=[Candidate(lexical_chunk, lexical_score=0.8)],
        vector_candidates=[Candidate(vector_chunk, vector_score=1.0)],
    )
    ranked = CandidateRanker(load_retrieval_config().ranking).rank(
        fused, max_per_source_object=3
    )

    assert [candidate.id for candidate in ranked] == ["chunk_vector", "chunk_lexical"]
    assert ranked[0].score_provenance == {"vector": 1.0}


def test_hybrid_fusion_applies_workspace_provider_and_active_status_filters(
    phase4_source_object,
) -> None:
    chunker = SourceAwareChunker(load_retrieval_config().chunking)
    base = chunker.chunks_for_source_object(phase4_source_object)[0]
    github = base.model_copy(
        update={
            "id": "chunk_github",
            "metadata_json": {"provider": "github"},
        }
    )
    other_workspace = base.model_copy(
        update={
            "id": "chunk_other_workspace",
            "workspace_id": "ws_2",
            "metadata_json": {"provider": "github"},
        }
    )
    stale = base.model_copy(
        update={
            "id": "chunk_stale",
            "status": SourceChunkStatus.STALE,
            "metadata_json": {"provider": "github"},
        }
    )
    slack = base.model_copy(
        update={"id": "chunk_slack", "metadata_json": {"provider": "slack"}}
    )

    fused = HybridCandidateFuser().fuse(
        workspace_id="ws_1",
        lexical_candidates=[
            Candidate(github, lexical_score=1.0),
            Candidate(other_workspace, lexical_score=1.0),
            Candidate(stale, lexical_score=1.0),
            Candidate(slack, lexical_score=1.0),
        ],
        vector_candidates=[],
        provider_filters=["github"],
    )

    assert [candidate.id for candidate in fused] == ["chunk_github"]


def test_hybrid_fusion_merges_duplicate_channel_scores_and_provenance(
    phase4_source_object,
) -> None:
    chunker = SourceAwareChunker(load_retrieval_config().chunking)
    chunk = chunker.chunks_for_source_object(phase4_source_object)[0]

    fused = HybridCandidateFuser().fuse(
        workspace_id="ws_1",
        lexical_candidates=[Candidate(chunk, lexical_score=0.7, paths={"keyword"})],
        vector_candidates=[Candidate(chunk, vector_score=0.9, paths={"semantic"})],
    )

    assert len(fused) == 1
    assert fused[0].paths == {"fts", "keyword", "semantic", "vector"}
    assert fused[0].score_provenance == {"lexical": 0.7, "vector": 0.9}


def test_hybrid_ranking_breaks_equal_scores_by_chunk_id(phase4_source_object) -> None:
    chunker = SourceAwareChunker(load_retrieval_config().chunking)
    base = chunker.chunks_for_source_object(phase4_source_object)[0]
    later = base.model_copy(update={"id": "chunk_z", "source_object_id": "so_z"})
    earlier = base.model_copy(update={"id": "chunk_a", "source_object_id": "so_a"})

    ranked = CandidateRanker(load_retrieval_config().ranking).rank(
        [Candidate(later, vector_score=1.0), Candidate(earlier, vector_score=1.0)],
        max_per_source_object=1,
    )

    assert [candidate.id for candidate in ranked] == ["chunk_a", "chunk_z"]


def test_hybrid_limit_uses_weighted_ranking_and_source_diversity(
    phase4_source_object,
) -> None:
    config = load_retrieval_config()
    base = SourceAwareChunker(config.chunking).chunks_for_source_object(
        phase4_source_object
    )[0]
    lexical_peak = base.model_copy(
        update={"id": "chunk_a_lexical", "source_object_id": "source_a"}
    )
    vector_best = base.model_copy(
        update={"id": "chunk_a_vector", "source_object_id": "source_a"}
    )
    second_source = base.model_copy(
        update={"id": "chunk_b_vector", "source_object_id": "source_b"}
    )

    fused = HybridCandidateFuser().fuse(
        workspace_id="ws_1",
        lexical_candidates=[Candidate(lexical_peak, lexical_score=1.0)],
        vector_candidates=[
            Candidate(vector_best, vector_score=0.8),
            Candidate(second_source, vector_score=0.7),
        ],
        limit=2,
        ranker=CandidateRanker(config.ranking),
        max_per_source_object=1,
    )

    # The raw lexical maximum is 1.0, but configured vector weighting ranks
    # chunk_a_vector first; per-source limiting keeps the second result diverse.
    assert [candidate.id for candidate in fused] == ["chunk_a_vector", "chunk_b_vector"]
