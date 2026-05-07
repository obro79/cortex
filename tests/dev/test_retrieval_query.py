from cortex.dev.fixtures import fixture_ids
from cortex.dev.workbench import DevWorkbenchService


def test_cor_123_query_returns_expected_sources_and_inspector_sections() -> None:
    service = DevWorkbenchService()
    service.seed()
    result = service.query("I am implementing Linear issue COR-123")

    assert set(result["expected_sources"]) == set(fixture_ids())
    assert {candidate["fixture_id"] for candidate in result["final_ranking"]} == set(
        fixture_ids()
    )
    assert result["lexical_candidates"]
    assert result["vector_candidates"]
    assert result["relationship_expansions"]
    assert result["merged_candidates"]
    assert result["excluded_candidates"] == []
    assert result["gate_status"] == "block"


def test_retrieval_output_is_stable_across_repeated_queries() -> None:
    service = DevWorkbenchService()
    service.seed()
    first = service.query("COR-123")
    second = service.query("COR-123")

    assert first["final_ranking"] == second["final_ranking"]
    assert first["evidence_pack_id"] == second["evidence_pack_id"]
