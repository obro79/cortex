from cortex.retrieval.query import QueryPlanner


def test_query_planner_extracts_issue_pr_paths_and_allowlist_hash() -> None:
    plan = QueryPlanner().plan(
        query="I'm implementing COR-123 from PR #184 in docs/session.md",
        provider_filters=["linear", "github"],
        source_allowlist=["so_1", "so_2"],
    )

    assert plan.normalized_query.startswith("i'm implementing cor-123")
    assert plan.issue_ids == ["COR-123"]
    assert plan.pr_numbers == ["184"]
    assert plan.file_paths == ["docs/session.md"]
    assert plan.provider_filters == ["github", "linear"]
    assert plan.source_allowlist_snapshot_hash is not None
