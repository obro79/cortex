"""Machine-readable acceptance checks for the synthetic COR-123 corpus.

This module deliberately evaluates safe citation metadata rather than source
content or an LLM response.  It can therefore run against a manifest plus an
in-memory retrieval projection during local rehearsal and against normalized
retrieval results in integration tests.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Protocol, cast

REQUIRED_PROVIDERS = frozenset(
    {"slack", "github", "jira", "email", "google_drive", "agent_session"}
)
FORBIDDEN_DATA_FIELDS = frozenset(
    {
        "authorization",
        "credential",
        "credentials",
        "native_session_handle",
        "native_session_id",
        "password",
        "private_url",
        "raw_payload",
        "secret",
        "token",
        "transcript",
        "vector_payload",
        "webhook_body",
    }
)


class ManifestRecord(Protocol):
    """The stable subset of a demo manifest record used by this evaluator."""

    fixture_id: str
    provider: str
    decisive: bool
    source_updated_at: datetime
    is_stale: bool


class EvidenceManifest(Protocol):
    """Public manifest API required by :class:`EvidenceContractEvaluator`."""

    task_ref: str
    records: Sequence[ManifestRecord]


@dataclass(frozen=True)
class EvidenceCitation:
    """Safe, normalized citation projection accepted by the contract."""

    fixture_id: str
    provider: str
    task_ref: str
    source_updated_at: datetime
    mode: str
    freshness: str
    relationship_state: str = "supporting"
    metadata: Mapping[str, object] | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> EvidenceCitation:
        timestamp = value.get("source_updated_at")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if not isinstance(timestamp, datetime):
            raise ValueError("citation source_updated_at must be an ISO timestamp")
        return cls(
            fixture_id=_required_text(value, "fixture_id"),
            provider=_required_text(value, "provider"),
            task_ref=_required_text(value, "task_ref"),
            source_updated_at=timestamp,
            mode=_required_text(value, "mode"),
            freshness=_required_text(value, "freshness"),
            relationship_state=str(value.get("relationship_state", "supporting")),
            metadata=_mapping_or_none(value.get("metadata")),
        )


@dataclass(frozen=True)
class EvidenceContractPolicy:
    expected_records: int = 189
    expected_decisive: int = 6
    expected_near_misses: int = 30
    required_providers: frozenset[str] = REQUIRED_PROVIDERS
    forbidden_data_fields: frozenset[str] = FORBIDDEN_DATA_FIELDS


@dataclass(frozen=True)
class EvidenceContractFailure:
    code: str
    expected: object
    observed: object


@dataclass(frozen=True)
class EvidenceContractReport:
    task_ref: str
    passed: bool
    expected_decisive_fixture_ids: tuple[str, ...]
    observed_citation_fixture_ids: tuple[str, ...]
    observed_providers: tuple[str, ...]
    corpus_record_count: int
    near_miss_count: int
    failures: tuple[EvidenceContractFailure, ...]

    def as_dict(self) -> dict[str, object]:
        return cast(dict[str, object], _json_ready(asdict(self)))


class EvidenceContractEvaluator:
    """Evaluate deterministic safe evidence metadata against a corpus manifest."""

    def __init__(self, policy: EvidenceContractPolicy | None = None) -> None:
        self._policy = policy or EvidenceContractPolicy()

    def evaluate(
        self,
        manifest: EvidenceManifest,
        citations: Iterable[EvidenceCitation | Mapping[str, object]],
    ) -> EvidenceContractReport:
        records = tuple(manifest.records)
        normalized_citations = tuple(
            _coerce_citation(citation) for citation in citations
        )
        failures: list[EvidenceContractFailure] = []
        decisive_records = tuple(record for record in records if record.decisive)
        decisive_ids = tuple(sorted(record.fixture_id for record in decisive_records))
        near_misses = tuple(record for record in records if _is_near_miss(record))

        self._expect(
            failures,
            "corpus_record_count",
            self._policy.expected_records,
            len(records),
        )
        self._expect(
            failures,
            "decisive_record_count",
            self._policy.expected_decisive,
            len(decisive_records),
        )
        self._expect(
            failures,
            "near_miss_count",
            self._policy.expected_near_misses,
            len(near_misses),
        )

        citation_by_id = {
            citation.fixture_id: citation for citation in normalized_citations
        }
        observed_ids = tuple(citation.fixture_id for citation in normalized_citations)
        missing_decisive = sorted(set(decisive_ids) - set(citation_by_id))
        if missing_decisive:
            failures.append(
                EvidenceContractFailure(
                    "missing_decisive_citations", decisive_ids, tuple(missing_decisive)
                )
            )
        near_miss_ids = {record.fixture_id for record in near_misses}
        displaced = sorted(set(observed_ids) & near_miss_ids)
        if displaced:
            failures.append(
                EvidenceContractFailure("near_miss_cited", (), tuple(displaced))
            )

        decisive_providers = {record.provider for record in decisive_records}
        self._expect(
            failures,
            "decisive_provider_coverage",
            tuple(sorted(self._policy.required_providers)),
            tuple(sorted(decisive_providers)),
        )
        observed_providers = tuple(
            sorted({citation.provider for citation in normalized_citations})
        )
        self._expect(
            failures,
            "citation_provider_coverage",
            tuple(sorted(self._policy.required_providers)),
            observed_providers,
        )

        wrong_scope = tuple(
            citation.fixture_id
            for citation in normalized_citations
            if citation.task_ref != manifest.task_ref
        )
        if wrong_scope:
            failures.append(
                EvidenceContractFailure(
                    "citation_task_scope", manifest.task_ref, wrong_scope
                )
            )

        self._validate_drive_conflict(failures, decisive_records, citation_by_id)
        self._validate_slack_priority(failures, decisive_records, normalized_citations)
        self._validate_forbidden_data(failures, normalized_citations)

        return EvidenceContractReport(
            task_ref=manifest.task_ref,
            passed=not failures,
            expected_decisive_fixture_ids=decisive_ids,
            observed_citation_fixture_ids=observed_ids,
            observed_providers=observed_providers,
            corpus_record_count=len(records),
            near_miss_count=len(near_misses),
            failures=tuple(failures),
        )

    @staticmethod
    def _expect(
        failures: list[EvidenceContractFailure],
        code: str,
        expected: object,
        observed: object,
    ) -> None:
        if expected != observed:
            failures.append(EvidenceContractFailure(code, expected, observed))

    def _validate_drive_conflict(
        self,
        failures: list[EvidenceContractFailure],
        decisive_records: Sequence[ManifestRecord],
        citation_by_id: Mapping[str, EvidenceCitation],
    ) -> None:
        stale_drive = tuple(
            record
            for record in decisive_records
            if record.provider == "google_drive" and record.is_stale
        )
        if len(stale_drive) != 1:
            failures.append(
                EvidenceContractFailure(
                    "stale_drive_manifest_contract", 1, len(stale_drive)
                )
            )
            return
        citation = citation_by_id.get(stale_drive[0].fixture_id)
        observed = (
            None
            if citation is None
            else {
                "freshness": citation.freshness,
                "relationship_state": citation.relationship_state,
            }
        )
        expected = {"freshness": "stale", "relationship_state": "conflicting"}
        if observed != expected:
            failures.append(
                EvidenceContractFailure("stale_drive_conflict", expected, observed)
            )

    def _validate_slack_priority(
        self,
        failures: list[EvidenceContractFailure],
        decisive_records: Sequence[ManifestRecord],
        citations: Sequence[EvidenceCitation],
    ) -> None:
        slack_records = tuple(
            record for record in decisive_records if record.provider == "slack"
        )
        if len(slack_records) != 1:
            failures.append(
                EvidenceContractFailure(
                    "slack_manifest_contract", 1, len(slack_records)
                )
            )
            return
        slack_id = slack_records[0].fixture_id
        positions = {
            citation.fixture_id: index for index, citation in enumerate(citations)
        }
        slack_position = positions.get(slack_id)
        slack = citations[slack_position] if slack_position is not None else None
        if slack is None or slack.freshness != "fresh":
            failures.append(
                EvidenceContractFailure(
                    "fresh_slack_required",
                    "fresh",
                    None if slack is None else slack.freshness,
                )
            )
            return
        if slack.mode != "live":
            failures.append(
                EvidenceContractFailure("fresh_slack_mode", "live", slack.mode)
            )
        decisive_positions = [
            positions[record.fixture_id]
            for record in decisive_records
            if record.fixture_id in positions
        ]
        if decisive_positions and slack_position != min(decisive_positions):
            failures.append(
                EvidenceContractFailure(
                    "fresh_slack_priority",
                    "first decisive citation",
                    slack_position,
                )
            )

    def _validate_forbidden_data(
        self,
        failures: list[EvidenceContractFailure],
        citations: Sequence[EvidenceCitation],
    ) -> None:
        forbidden_paths: list[str] = []
        for citation in citations:
            if citation.metadata is not None:
                forbidden_paths.extend(
                    f"{citation.fixture_id}.{path}"
                    for path in _forbidden_paths(
                        citation.metadata, self._policy.forbidden_data_fields
                    )
                )
        if forbidden_paths:
            failures.append(
                EvidenceContractFailure(
                    "forbidden_data_exposed", (), tuple(sorted(forbidden_paths))
                )
            )


def _coerce_citation(
    citation: EvidenceCitation | Mapping[str, object],
) -> EvidenceCitation:
    return (
        citation
        if isinstance(citation, EvidenceCitation)
        else EvidenceCitation.from_mapping(citation)
    )


def _is_near_miss(record: ManifestRecord) -> bool:
    """Support explicit v2 labels while keeping compatibility with frozen v1 data."""
    for name in ("near_miss", "is_near_miss"):
        if bool(getattr(record, name, False)):
            return True
    return (
        getattr(record, "role", None) == "near_miss"
        or getattr(record, "evidence_class", None) == "near_miss"
    )


def _required_text(value: Mapping[str, object], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item:
        raise ValueError(f"citation {field} must be a non-empty string")
    return item


def _mapping_or_none(value: object) -> Mapping[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("citation metadata must be an object")
    return value


def _forbidden_paths(
    value: object, forbidden_fields: frozenset[str], path: str = ""
) -> list[str]:
    if not isinstance(value, Mapping):
        if isinstance(value, list):
            paths: list[str] = []
            for index, child in enumerate(value):
                paths.extend(
                    _forbidden_paths(child, forbidden_fields, f"{path}[{index}]")
                )
            return paths
        return []
    paths = []
    for key, child in value.items():
        child_path = f"{path}.{key}" if path else str(key)
        if str(key).lower() in forbidden_fields:
            paths.append(child_path)
        paths.extend(_forbidden_paths(child, forbidden_fields, child_path))
    return paths


def _json_ready(value: object) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(child) for child in value]
    return value
