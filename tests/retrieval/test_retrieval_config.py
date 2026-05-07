import pytest

from cortex.chunking.config import load_retrieval_config
from cortex.retrieval.ranking import CandidateRanker


def test_retrieval_config_token_budget_and_ranking_weights() -> None:
    config = load_retrieval_config()

    assert config.candidate_retrieval["version"] == "candidate-retrieval-v1"
    assert config.token_budget is not None
    assert config.token_budget["max_evidence_pack_tokens"] == 4000
    CandidateRanker(config.ranking)


def test_ranker_rejects_base_weights_that_do_not_sum_to_one() -> None:
    weights = {
        "vector_weight": 0.5,
        "lexical_weight": 0.5,
        "recency_weight": 0.5,
        "relationship_weight": 0,
        "source_authority_weight": 0,
        "version": "ranking-v1",
    }

    with pytest.raises(ValueError, match="sum to 1.0"):
        CandidateRanker(weights)
