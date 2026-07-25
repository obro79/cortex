from typing import Any

from cortex.canonical_memory.publishers import CanonicalDecisionPublisher
from cortex.canonical_memory.repositories import (
    InMemoryApprovalRecordRepository,
    InMemoryCanonicalDecisionRepository,
)
from cortex.canonical_memory.service import CanonicalDecisionService
from cortex.context_gate.publishers import ContextGatePublisher
from cortex.context_gate.repositories import InMemoryContextGateResultRepository
from cortex.context_gate.service import ContextGateService
from cortex.events.in_memory import InMemoryEventBus
from cortex.retrieval.defaults import create_empty_retrieval_service

TOOL_NAMES = (
    "retrieve_context",
    "get_related_work",
    "check_context_gate",
    "propose_canonical_decision",
    "approve_canonical_decision",
)

_canonical_decisions = InMemoryCanonicalDecisionRepository()
_approval_records = InMemoryApprovalRecordRepository()
_retrieval_service = create_empty_retrieval_service()
_retrieval_service.canonical_decisions = _canonical_decisions
_context_gate_event_bus = InMemoryEventBus()
_context_gate_results = InMemoryContextGateResultRepository()
_context_gate_service = ContextGateService(
    retrieval_service=_retrieval_service,
    repository=_context_gate_results,
    publisher=ContextGatePublisher(_context_gate_event_bus),
)
_canonical_service = CanonicalDecisionService(
    decisions=_canonical_decisions,
    approvals=_approval_records,
    evidence=_retrieval_service.evidence,
    gates=_context_gate_results,
    publisher=CanonicalDecisionPublisher(InMemoryEventBus()),
)


def list_tools() -> tuple[str, ...]:
    return TOOL_NAMES


async def call_tool(
    name: str, arguments: dict[str, Any] | None = None
) -> dict[str, Any]:
    if name not in TOOL_NAMES:
        return {"ok": False, "error": "unknown_tool", "tool": name}
    if name in {"retrieve_context", "get_related_work"}:
        args = arguments or {}
        allowed = {"workspace_id", "query", "source_allowlist", "provider_filters"}
        unknown = sorted(set(args) - allowed)
        if unknown:
            return {"ok": False, "error": "unknown_arguments", "fields": unknown}
        if "workspace_id" not in args or "query" not in args:
            return {"ok": False, "error": "missing_required_arguments"}
        response = await getattr(_retrieval_service, name)(
            workspace_id=str(args["workspace_id"]),
            query=str(args["query"]),
            source_allowlist=list(args.get("source_allowlist", [])),
            provider_filters=list(args.get("provider_filters", [])),
        )
        return {
            "ok": response.ok,
            "tool": name,
            "retrieval_request_id": response.retrieval_request_id,
            "evidence_pack_id": response.evidence_pack_id,
            "text": response.text,
            "evidence_pack": response.evidence_pack,
            "status": response.status,
            "latency_ms": response.latency_ms,
        }
    if name == "check_context_gate":
        args = arguments or {}
        allowed = {
            "workspace_id",
            "query",
            "evidence_pack_id",
            "task_hints",
            "source_allowlist",
            "provider_filters",
        }
        unknown = sorted(set(args) - allowed)
        if unknown:
            return {"ok": False, "error": "unknown_arguments", "fields": unknown}
        if "workspace_id" not in args:
            return {"ok": False, "error": "missing_required_arguments"}
        if "query" not in args and "evidence_pack_id" not in args:
            return {"ok": False, "error": "missing_required_arguments"}
        response = await _context_gate_service.check_context_gate(
            workspace_id=str(args["workspace_id"]),
            query=str(args["query"]) if "query" in args else None,
            evidence_pack_id=(
                str(args["evidence_pack_id"]) if "evidence_pack_id" in args else None
            ),
            task_hints=dict(args.get("task_hints", {})),
            source_allowlist=list(args.get("source_allowlist", [])),
            provider_filters=list(args.get("provider_filters", [])),
        )
        return {
            "ok": response.ok,
            "tool": name,
            "context_gate_result_id": response.context_gate_result_id,
            "status": response.status,
            "text": response.text,
            "result": response.result,
            **({"error": response.error} if response.error else {}),
        }
    if name == "propose_canonical_decision":
        args = arguments or {}
        allowed = {
            "workspace_id",
            "evidence_pack_id",
            "context_gate_result_id",
            "scope_type",
            "scope_ref",
            "title",
            "decision_text",
            "actor_id",
        }
        unknown = sorted(set(args) - allowed)
        if unknown:
            return {"ok": False, "error": "unknown_arguments", "fields": unknown}
        if "workspace_id" not in args:
            return {"ok": False, "error": "missing_required_arguments"}
        if "evidence_pack_id" not in args and "context_gate_result_id" not in args:
            return {"ok": False, "error": "missing_required_arguments"}
        response = _canonical_service.propose_canonical_decision(
            workspace_id=str(args["workspace_id"]),
            evidence_pack_id=(
                str(args["evidence_pack_id"]) if "evidence_pack_id" in args else None
            ),
            context_gate_result_id=(
                str(args["context_gate_result_id"])
                if "context_gate_result_id" in args
                else None
            ),
            scope_type=str(args["scope_type"]) if "scope_type" in args else None,
            scope_ref=str(args["scope_ref"]) if "scope_ref" in args else None,
            title=str(args["title"]) if "title" in args else None,
            decision_text=(
                str(args["decision_text"]) if "decision_text" in args else None
            ),
            actor_id=str(args["actor_id"]) if "actor_id" in args else None,
        )
        return {
            "ok": response.ok,
            "tool": name,
            "text": response.text,
            "result": response.result,
            **({"error": response.error} if response.error else {}),
        }
    if name == "approve_canonical_decision":
        args = arguments or {}
        allowed = {
            "decision_id",
            "action",
            "actor_id",
            "final_text",
            "rationale",
            "supersedes_decision_id",
        }
        unknown = sorted(set(args) - allowed)
        if unknown:
            return {"ok": False, "error": "unknown_arguments", "fields": unknown}
        if "decision_id" not in args or "action" not in args:
            return {"ok": False, "error": "missing_required_arguments"}
        response = await _canonical_service.approve_canonical_decision(
            decision_id=str(args["decision_id"]),
            action=str(args["action"]),
            actor_id=str(args["actor_id"]) if "actor_id" in args else None,
            final_text=str(args["final_text"]) if "final_text" in args else None,
            rationale=str(args["rationale"]) if "rationale" in args else None,
            supersedes_decision_id=(
                str(args["supersedes_decision_id"])
                if "supersedes_decision_id" in args
                else None
            ),
        )
        return {
            "ok": response.ok,
            "tool": name,
            "text": response.text,
            "result": response.result,
            **({"error": response.error} if response.error else {}),
        }
    return {
        "ok": False,
        "tool": name,
        "reason": "not_implemented",
        "arguments": arguments or {},
    }
