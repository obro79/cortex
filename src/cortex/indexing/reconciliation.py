"""Content-free derived-index reconciliation and readiness projections.

Postgres remains authoritative. These helpers compare only stable logical point
IDs and compact Qdrant filter metadata, never source content.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ExpectedIndexPoint:
    """The current canonical expectation for one derived vector point."""

    point_id: str
    metadata: Mapping[str, str | int | bool | list[str] | list[int]]


@dataclass(frozen=True)
class ActualIndexPoint:
    """A content-free observation made from the derived vector store."""

    point_id: str
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class IndexReadinessProjection:
    """A deterministic, conservative repair/readiness view."""

    expected_point_count: int
    actual_point_count: int
    missing_point_ids: tuple[str, ...]
    stale_point_ids: tuple[str, ...]
    orphan_point_ids: tuple[str, ...]

    @property
    def ready(self) -> bool:
        """True only after a complete observed point set matches expectations."""
        return not (
            self.missing_point_ids or self.stale_point_ids or self.orphan_point_ids
        )

    @property
    def repair_required(self) -> bool:
        return not self.ready


def project_index_readiness(
    *,
    expected_points: Iterable[ExpectedIndexPoint],
    actual_points: Iterable[ActualIndexPoint],
) -> IndexReadinessProjection:
    """Compare expected current points with a Qdrant inventory observation.

    Duplicate logical IDs are a bad inventory observation and therefore leave
    the projection not-ready. A caller must observe actual points; an upsert
    acknowledgement alone is not input to this projection.
    """
    expected = _unique_expected(expected_points)
    actual, duplicate_actual_ids = _actual_by_id(actual_points)
    expected_ids = set(expected)
    actual_ids = set(actual)
    missing = expected_ids - actual_ids
    orphan = (actual_ids - expected_ids) | duplicate_actual_ids
    stale = {
        point_id
        for point_id in expected_ids & actual_ids
        if not _metadata_matches(expected[point_id].metadata, actual[point_id].metadata)
    }
    return IndexReadinessProjection(
        expected_point_count=len(expected),
        actual_point_count=len(actual),
        missing_point_ids=tuple(sorted(missing)),
        stale_point_ids=tuple(sorted(stale)),
        orphan_point_ids=tuple(sorted(orphan)),
    )


def _unique_expected(
    points: Iterable[ExpectedIndexPoint],
) -> dict[str, ExpectedIndexPoint]:
    records: dict[str, ExpectedIndexPoint] = {}
    for point in points:
        if point.point_id in records:
            raise ValueError(f"duplicate expected logical point ID: {point.point_id}")
        records[point.point_id] = point
    return records


def _actual_by_id(
    points: Iterable[ActualIndexPoint],
) -> tuple[dict[str, ActualIndexPoint], set[str]]:
    records: dict[str, ActualIndexPoint] = {}
    duplicates: set[str] = set()
    for point in points:
        if point.point_id in records:
            duplicates.add(point.point_id)
            continue
        records[point.point_id] = point
    return records, duplicates


def _metadata_matches(
    expected: Mapping[str, object], actual: Mapping[str, object]
) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())
