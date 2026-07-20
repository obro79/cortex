"""The MCP-first, evidence-only task context v1 contract."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .service import RetrievalServiceResponse

CONTRACT_VERSION: Final[Literal["cortex.task_context.v1"]] = "cortex.task_context.v1"
MAX_EVIDENCE_ITEMS = 12
MAX_TOKENS = 4_000
ErrorCode = Literal[
    "INVALID_ARGUMENTS",
    "AUTH_REQUIRED",
    "AUTH_EXPIRED",
    "WORKSPACE_UNAVAILABLE",
    "SOURCE_SCOPE_DENIED",
    "FRESHNESS_REQUIREMENT_UNMET",
    "CONTEXT_RUNTIME_UNAVAILABLE",
    "RETRIEVAL_UNAVAILABLE",
    "RATE_LIMITED",
    "INTERNAL_ERROR",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskHints(_StrictModel):
    objective: str = Field(min_length=1, max_length=4_000)
    repository: str | None = Field(default=None, max_length=500)
    branch: str | None = Field(default=None, max_length=500)
    issue_ids: list[str] = Field(default_factory=list, max_length=50)
    pull_request_numbers: list[int] = Field(default_factory=list, max_length=50)
    file_hints: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("objective")
    @classmethod
    def objective_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("objective must not be blank")
        return value.strip()


class TaskContextFilters(_StrictModel):
    providers: list[str] = Field(default_factory=list, max_length=20)
    source_ids: list[str] = Field(default_factory=list, max_length=100)


class FreshnessRequest(_StrictModel):
    maximum_age_seconds: int = Field(default=3_600, ge=1, le=2_592_000)
    require_fresh: bool = False


class ContextBudget(_StrictModel):
    maximum_evidence_items: int = Field(default=MAX_EVIDENCE_ITEMS, ge=1)
    maximum_tokens: int = Field(default=MAX_TOKENS, ge=1)

    @property
    def evidence_items(self) -> int:
        return min(self.maximum_evidence_items, MAX_EVIDENCE_ITEMS)

    @property
    def tokens(self) -> int:
        return min(self.maximum_tokens, MAX_TOKENS)


class TaskContextRequest(_StrictModel):
    task: TaskHints
    filters: TaskContextFilters = Field(default_factory=TaskContextFilters)
    freshness: FreshnessRequest = Field(default_factory=FreshnessRequest)
    budget: ContextBudget = Field(default_factory=ContextBudget)


class TaskContextError(_StrictModel):
    code: ErrorCode
    message: str
    retryable: bool = False
    retry_after_seconds: int | None = Field(default=None, ge=1)


class TaskEvidence(_StrictModel):
    citation_id: str
    provider: str
    source_type: str
    source_object_id: str
    label: str | None = None
    snippet: str
    citation_url: str | None = None
    source_updated_at: str | None = None
    last_synced_at: str | None = None
    freshness: Literal["fresh", "mixed", "stale", "unknown"]
    retrieval_paths: list[str]
    score_provenance: dict[str, float]
    content_hash: str | None = None
    source_version: str | None = None


class TaskContextResult(_StrictModel):
    evidence_items: list[TaskEvidence]
    source_coverage: dict[str, Any]
    freshness: dict[str, Any]
    conflicts: list[dict[str, Any]]
    missing_context: list[dict[str, Any]]
    retrieval: dict[str, Any]
    versions: dict[str, str]


class TaskContextResponse(_StrictModel):
    contract_version: Literal["cortex.task_context.v1"] = CONTRACT_VERSION
    ok: bool
    status: Literal["complete", "partial", "no_context", "denied", "failed"]
    request_id: str | None = None
    evidence_pack_id: str | None = None
    trace_id: str
    live_data: bool
    task_context: TaskContextResult | None = None
    warnings: list[str] = Field(default_factory=list)
    error: TaskContextError | None = None

    @classmethod
    def error_response(
        cls,
        *,
        trace_id: str,
        live_data: bool,
        code: ErrorCode,
        message: str,
        retryable: bool = False,
        retry_after_seconds: int | None = None,
        status: Literal["denied", "failed"] = "failed",
    ) -> TaskContextResponse:
        return cls(
            ok=False,
            status=status,
            trace_id=trace_id,
            live_data=live_data,
            error=TaskContextError(
                code=code,
                message=message,
                retryable=retryable,
                retry_after_seconds=retry_after_seconds,
            ),
        )


class TaskContextService:
    """Project an already-authorized retrieval response into the stable v1 DTO.

    Retrieval remains responsible for canonical hydration and permission checks;
    this service deliberately never accepts identity or tenancy fields.
    """

    def project(
        self,
        *,
        request: TaskContextRequest,
        response: RetrievalServiceResponse,
        trace_id: str,
        live_data: bool,
    ) -> TaskContextResponse:
        if not response.ok:
            return TaskContextResponse.error_response(
                trace_id=trace_id,
                live_data=live_data,
                code="RETRIEVAL_UNAVAILABLE",
                message="Task context is temporarily unavailable.",
                retryable=True,
                retry_after_seconds=10,
            )
        pack = response.evidence_pack
        summary = _mapping(pack.get("candidate_summary_json"))
        errors = _mapping(summary.get("errors"))
        citations = _items(_mapping(pack.get("citations_json")).get("items"))[
            : request.budget.evidence_items
        ]
        per_item_tokens = max(1, request.budget.tokens // max(1, len(citations)))
        evidence = [
            self._evidence(
                item,
                maximum_age=request.freshness.maximum_age_seconds,
                maximum_tokens=per_item_tokens,
            )
            for item in citations
        ]
        if request.freshness.require_fresh:
            evidence = [item for item in evidence if item.freshness == "fresh"]
            if not evidence:
                return TaskContextResponse.error_response(
                    trace_id=trace_id,
                    live_data=live_data,
                    code="FRESHNESS_REQUIREMENT_UNMET",
                    message="No fresh authorized task context is available.",
                )
        status: Literal["complete", "partial", "no_context"]
        if not evidence:
            status = "no_context"
        elif errors or any(item.freshness != "fresh" for item in evidence):
            status = "partial"
        else:
            status = "complete"
        requested = sorted(set(request.filters.providers))
        returned = sorted({item.provider for item in evidence})
        warnings: list[str] = []
        if errors:
            warnings.append("One or more retrieval paths were unavailable.")
        if any(item.freshness in {"stale", "mixed", "unknown"} for item in evidence):
            warnings.append(
                "Some returned evidence does not satisfy the requested "
                "freshness target."
            )
        versions = {
            str(key): str(value)
            for key, value in _mapping(summary.get("versions")).items()
        }
        lexical_count = _integer(summary.get("lexical_candidate_count"))
        vector_count = _integer(summary.get("vector_candidate_count"))
        retrieval_status = _retrieval_status(errors, lexical_count, vector_count)
        return TaskContextResponse(
            ok=True,
            status=status,
            request_id=response.retrieval_request_id,
            evidence_pack_id=response.evidence_pack_id,
            trace_id=trace_id,
            live_data=live_data,
            task_context=TaskContextResult(
                evidence_items=evidence,
                source_coverage={
                    "providers_requested": requested,
                    "providers_returned": returned,
                    "evidence_item_count": len(evidence),
                },
                freshness={
                    "status": _pack_freshness(evidence),
                    "oldest_sync_at": _oldest_sync(evidence),
                    "maximum_age_seconds": request.freshness.maximum_age_seconds,
                },
                conflicts=_conflicts(pack),
                missing_context=_missing_context(pack),
                retrieval={
                    "status": retrieval_status,
                    "lexical_candidate_count": lexical_count,
                    "vector_candidate_count": vector_count,
                    "partial_reasons": sorted(errors),
                },
                versions=versions,
            ),
            warnings=warnings,
        )

    def _evidence(
        self, citation: dict[str, Any], *, maximum_age: int, maximum_tokens: int
    ) -> TaskEvidence:
        synced = _string(citation.get("last_synced_at"))
        source_updated = _string(citation.get("source_updated_at"))
        return TaskEvidence(
            citation_id=_string(citation.get("source_chunk_id")) or "unknown",
            provider=_string(citation.get("provider")) or "unknown",
            source_type=_string(citation.get("source_type")) or "unknown",
            source_object_id=_string(citation.get("source_object_id")) or "unknown",
            label=_string(citation.get("citation_label")),
            snippet=_limit_tokens(
                _string(citation.get("snippet")) or "", maximum_tokens
            ),
            citation_url=_string(citation.get("citation_url")),
            source_updated_at=source_updated,
            last_synced_at=synced,
            freshness=_freshness(synced, maximum_age),
            retrieval_paths=sorted(_strings(citation.get("retrieval_paths"))),
            score_provenance={
                str(key): float(value)
                for key, value in _mapping(citation.get("score_provenance")).items()
                if isinstance(value, int | float)
            },
            content_hash=_string(citation.get("content_hash")),
            source_version=_string(citation.get("source_version")),
        )


def invalid_arguments_response(
    *, trace_id: str, live_data: bool
) -> TaskContextResponse:
    return TaskContextResponse.error_response(
        trace_id=trace_id,
        live_data=live_data,
        code="INVALID_ARGUMENTS",
        message="Task context arguments are invalid.",
    )


def parse_task_context_request(arguments: object) -> TaskContextRequest:
    return TaskContextRequest.model_validate(arguments)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _items(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _freshness(
    timestamp: str | None, maximum_age: int
) -> Literal["fresh", "mixed", "stale", "unknown"]:
    if timestamp is None:
        return "unknown"
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    if parsed.tzinfo is None:
        return "unknown"
    age_seconds = (datetime.now(UTC) - parsed).total_seconds()
    return "fresh" if age_seconds <= maximum_age else "stale"


def _pack_freshness(evidence: list[TaskEvidence]) -> str:
    statuses = {item.freshness for item in evidence}
    if not statuses:
        return "unknown"
    if len(statuses) > 1:
        return "mixed"
    return next(iter(statuses))


def _oldest_sync(evidence: list[TaskEvidence]) -> str | None:
    values = [item.last_synced_at for item in evidence if item.last_synced_at]
    return min(values) if values else None


def _limit_tokens(value: str, maximum_tokens: int) -> str:
    return " ".join(value.split()[:maximum_tokens])


def _retrieval_status(errors: dict[str, Any], lexical: int, vector: int) -> str:
    if "vector" in errors and lexical:
        return "fts_only"
    if "fts" in errors and vector:
        return "vector_only"
    if errors:
        return "unavailable"
    return "hybrid"


def _conflicts(pack: dict[str, object]) -> list[dict[str, Any]]:
    summary = _mapping(pack.get("conflict_summary_json"))
    return [summary] if _integer(summary.get("conflict_count")) else []


def _missing_context(pack: dict[str, object]) -> list[dict[str, Any]]:
    summary = _mapping(pack.get("missing_context_json"))
    return [summary] if summary else []
