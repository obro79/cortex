from cortex.chunking.config import load_retrieval_config
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.retrieval.candidates import Candidate
from cortex.retrieval.ranking import CandidateRanker


def test_ranking_deduplicates_and_prefers_exact_lexical_candidate(
    phase4_source_object,
) -> None:
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(phase4_source_object)[0]
    ranker = CandidateRanker(load_retrieval_config().ranking)

    ranked = ranker.rank(
        [
            Candidate(chunk, vector_score=0.2, paths={"vector"}),
            Candidate(chunk, lexical_score=1.0, paths={"fts"}),
        ],
        max_per_source_object=3,
    )

    assert len(ranked) == 1
    assert ranked[0].paths == {"vector", "fts"}
    assert ranker.score(ranked[0]) > 0
