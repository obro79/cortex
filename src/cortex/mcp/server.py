from typing import Any

from cortex.retrieval.defaults import create_empty_retrieval_service

TOOL_NAMES = (
    "retrieve_context",
    "get_related_work",
    "check_context_gate",
    "propose_canonical_decision",
    "approve_canonical_decision",
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
        service = create_empty_retrieval_service()
        response = await getattr(service, name)(
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
    return {
        "ok": False,
        "tool": name,
        "reason": "not_implemented",
        "arguments": arguments or {},
    }
