import asyncio
import json
import sys
from collections.abc import Mapping
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
from cortex.handoff import create_handoff_bundle
from cortex.retrieval.defaults import create_empty_retrieval_service

TOOL_NAMES = (
    "retrieve_context",
    "get_related_work",
    "check_context_gate",
    "propose_canonical_decision",
    "approve_canonical_decision",
    "create_handoff_bundle",
)

MCP_PROTOCOL_VERSION = "2024-11-05"

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
    if name == "create_handoff_bundle":
        return create_handoff_bundle(arguments or {})
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


def list_tool_definitions() -> list[dict[str, object]]:
    """Return MCP tool metadata, including the portable handoff contract."""
    definitions: list[dict[str, object]] = [
        {
            "name": name,
            "description": f"Cortex tool: {name}.",
            "inputSchema": {"type": "object"},
        }
        for name in TOOL_NAMES
    ]
    handoff = next(
        item for item in definitions if item["name"] == "create_handoff_bundle"
    )
    handoff.update(
        {
            "description": (
                "Create a portable handoff bundle from an approved summary and "
                "evidence references. Never accesses agent sessions."
            ),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["approved_summary"],
                "properties": {
                    "approved_summary": {"type": "string", "minLength": 1},
                    "evidence_references": {
                        "type": "array",
                        "items": {"type": ["string", "object"]},
                    },
                    "opaque_handles": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "handoff_opt_in": {"type": "boolean"},
                },
            },
        }
    )
    return definitions


def _json_rpc_error(request_id: object, code: int, message: str) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _is_valid_request_id(value: object) -> bool:
    """Return whether a JSON-RPC request id can be echoed safely."""
    return value is None or (
        isinstance(value, (str, int)) and not isinstance(value, bool)
    )


def _is_valid_method(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


async def handle_json_rpc_message(message: object) -> dict[str, object] | None:
    """Handle one JSON-RPC 2.0 request for the newline-delimited stdio server."""
    if not isinstance(message, Mapping) or message.get("jsonrpc") != "2.0":
        return _json_rpc_error(None, -32600, "Invalid Request")

    request_id = message.get("id")
    is_notification = "id" not in message
    method = message.get("method")
    params = message.get("params", {})
    if not is_notification and not _is_valid_request_id(request_id):
        return _json_rpc_error(None, -32600, "Invalid Request")
    if not _is_valid_method(method):
        if is_notification:
            return None
        return _json_rpc_error(request_id, -32600, "Invalid Request")
    if not isinstance(params, Mapping):
        if is_notification:
            return None
        return _json_rpc_error(request_id, -32602, "Invalid params")

    if method == "initialize":
        result: dict[str, object] = {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "cortex-mcp", "version": "0.1.0"},
        }
    elif method == "tools/list":
        result = {"tools": list_tool_definitions()}
    elif method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if (
            not isinstance(name, str)
            or not name.strip()
            or not isinstance(arguments, Mapping)
        ):
            if is_notification:
                return None
            return _json_rpc_error(request_id, -32602, "Invalid params")
        response = await call_tool(name, dict(arguments))
        result = {
            "content": [{"type": "text", "text": json.dumps(response, sort_keys=True)}],
            "structuredContent": response,
            "isError": not response.get("ok", False),
        }
    else:
        if is_notification:
            return None
        return _json_rpc_error(request_id, -32601, "Method not found")

    if is_notification:
        return None
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


async def serve_stdio() -> None:
    """Serve newline-delimited JSON-RPC over stdin/stdout without session access."""
    for line in sys.stdin:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response: dict[str, object] | None = _json_rpc_error(
                None, -32700, "Parse error"
            )
        else:
            response = await handle_json_rpc_message(message)
        if response is not None:
            sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
            sys.stdout.flush()


def main() -> None:
    """Console-script entry point for the local MCP stdio server."""
    asyncio.run(serve_stdio())


if __name__ == "__main__":
    main()
