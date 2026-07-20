import pytest

from cortex.indexing.reconciliation import (
    ActualIndexPoint,
    ExpectedIndexPoint,
    project_index_readiness,
)


def test_projection_is_ready_only_for_an_exact_current_observed_point_set() -> None:
    expected = [
        ExpectedIndexPoint(
            point_id="embedding_1",
            metadata={
                "workspace_id": "ws_1",
                "status": "active",
                "source_allowlist_eligible": True,
                "scope_revision": "scope-v2",
                "acl_revision": "acl-v3",
                "chunking_version": "chunk-v1",
                "embedding_version": "embedding-v1",
                "index_version": "index-v1",
            },
        )
    ]

    projection = project_index_readiness(
        expected_points=expected,
        actual_points=[ActualIndexPoint("embedding_1", dict(expected[0].metadata))],
    )

    assert projection.ready is True
    assert projection.repair_required is False


def test_projection_identifies_missing_stale_and_orphan_points() -> None:
    expected = [
        ExpectedIndexPoint("missing", {"status": "active"}),
        ExpectedIndexPoint("stale", {"acl_revision": "acl-v2"}),
    ]

    projection = project_index_readiness(
        expected_points=expected,
        actual_points=[
            ActualIndexPoint("stale", {"acl_revision": "acl-v1"}),
            ActualIndexPoint("orphan", {"status": "active"}),
        ],
    )

    assert projection.ready is False
    assert projection.repair_required is True
    assert projection.missing_point_ids == ("missing",)
    assert projection.stale_point_ids == ("stale",)
    assert projection.orphan_point_ids == ("orphan",)


def test_projection_rejects_duplicate_expected_logical_ids() -> None:
    with pytest.raises(ValueError, match="duplicate expected"):
        project_index_readiness(
            expected_points=[
                ExpectedIndexPoint("point_1", {}),
                ExpectedIndexPoint("point_1", {}),
            ],
            actual_points=[],
        )
