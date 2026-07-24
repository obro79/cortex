import asyncio
import json
import os
import sys
from collections.abc import Mapping
from typing import Any, Protocol

from cortex.canonical_memory.publishers import CanonicalDecisionPublisher
from cortex.canonical_memory.repositories import (
    InMemoryApprovalRecordRepository,
    InMemoryCanonicalDecisionRepository,
)
from cortex.canonical_memory.service import APPROVAL_ACTIONS, CanonicalDecisionService
from cortex.context_gate.publishers import ContextGatePublisher
from cortex.context_gate.repositories import InMemoryContextGateResultRepository
from cortex.context_gate.service import ContextGateService
from cortex.events.in_memory import InMemoryEventBus
from cortex.handoff import create_handoff_bundle
from cortex.retrieval.defaults import create_empty_retrieval_service
from cortex.retrieval.task_context import (
    TaskContextRequest,
    invalid_arguments_response,
    parse_task_context_request,
)
from cortex.runtime import CortexAuthority, CortexRuntime


class TaskContextProxy(Protocol):
    """Narrow transport seam for an API-backed task-context tool."""

    async def get_task_context(self, request: TaskContextRequest) -> dict[str, Any]: ...


TOOL_NAMES = (
    "get_task_context",
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
_local_runtime = CortexRuntime(
    retrieval=_retrieval_service, context_gate=_context_gate_service, live_data=False
)


class McpServer:
    """MCP adapter with a host-resolved authority and an injected runtime."""

    def __init__(
        self,
        *,
        runtime: CortexRuntime,
        authority: CortexAuthority,
        canonical_service: CanonicalDecisionService | None = None,
        task_context_proxy: TaskContextProxy | None = None,
        proxy_only: bool = False,
    ) -> None:
        self.runtime = runtime
        self.authority = authority
        self.canonical_service = canonical_service or _canonical_service_for_runtime(
            runtime
        )
        self.task_context_proxy = task_context_proxy
        self.proxy_only = proxy_only

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if self.proxy_only and name != "get_task_context":
            return {"ok": False, "error": "tool_unavailable_in_proxy_mode"}
        if name == "get_task_context" and self.task_context_proxy is not None:
            try:
                request = parse_task_context_request(arguments or {})
            except Exception:
                return invalid_arguments_response(
                    trace_id=self.authority.trace_id, live_data=False
                ).model_dump(mode="json", exclude_none=True)
            return await self.task_context_proxy.get_task_context(request)
        return await call_tool(
            name,
            arguments,
            runtime=self.runtime,
            authority=self.authority,
            canonical_service=self.canonical_service,
        )

    def tool_definitions(self) -> list[dict[str, object]]:
        """Return only the safe surface available to this server instance."""
        definitions = list_tool_definitions()
        if not self.proxy_only:
            return definitions
        return [
            definition
            for definition in definitions
            if definition["name"] == "get_task_context"
        ]


def create_fixture_server(*, workspace_id: str = "ws_1") -> McpServer:
    """Build the fixed-scope local fixture used only by tests and development.

    This is intentionally an opt-in factory: the stdio transport never derives
    a workspace from a client tool argument.
    """
    return McpServer(
        runtime=_local_runtime,
        authority=CortexAuthority(
            workspace_id=workspace_id,
            actor_id=None,
            trace_id="mcp-local-fixture",
        ),
        canonical_service=_canonical_service,
    )


def create_local_proxy_server(*, task_context_proxy: TaskContextProxy) -> McpServer:
    """Build an API-backed server with a fixed, non-client-supplied authority.

    Only ``get_task_context`` uses the proxy. Other retrieval tools remain
    unavailable in proxy mode.
    """
    return McpServer(
        runtime=_local_runtime,
        authority=CortexAuthority(
            workspace_id="mcp-proxy-configured",
            actor_id=None,
            trace_id="mcp-local-proxy",
        ),
        canonical_service=_canonical_service,
        task_context_proxy=task_context_proxy,
        proxy_only=True,
    )


def _canonical_service_for_runtime(runtime: CortexRuntime) -> CanonicalDecisionService:
    """Bind canonical decisions to evidence created by the injected runtime."""
    # ``CortexRuntime`` wraps the fixture RetrievalService in a typed adapter.
    # Unwrap only that local implementation here; durable adapters should be
    # supplied with an explicit canonical service by their composition root.
    retrieval = getattr(runtime.retrieval, "_retrieval", runtime.retrieval)
    evidence = getattr(retrieval, "evidence", None)
    gates = getattr(runtime.context_gate, "repository", None)
    if evidence is None:
        return _canonical_service
    decisions = InMemoryCanonicalDecisionRepository()
    # The local retrieval implementation consumes this repository to elevate
    # approved canonical decisions. Production composition roots may instead
    # provide their own canonical service explicitly.
    if hasattr(retrieval, "canonical_decisions"):
        retrieval.canonical_decisions = decisions
    return CanonicalDecisionService(
        decisions=decisions,
        approvals=InMemoryApprovalRecordRepository(),
        evidence=evidence,
        gates=gates or InMemoryContextGateResultRepository(),
        publisher=CanonicalDecisionPublisher(InMemoryEventBus()),
    )


def list_tools() -> tuple[str, ...]:
    return TOOL_NAMES


async def call_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    runtime: CortexRuntime | None = None,
    authority: CortexAuthority | None = None,
    canonical_service: CanonicalDecisionService | None = None,
) -> dict[str, Any]:
    """Call one tool.

    Production callers must construct :class:`McpServer` with host-derived
    authority. This compatibility function retains a deterministic, fixed-scope
    ``ws_1`` fixture for legacy local tests; it never trusts a client workspace
    claim to establish authority.
    """
    args = arguments or {}
    local_compatibility = runtime is None
    if runtime is None:
        runtime = _local_runtime
        authority = CortexAuthority(
            workspace_id="ws_1",
            actor_id=None,
            trace_id="mcp-local",
        )
        canonical_service = _canonical_service
    if authority is None:
        return {"ok": False, "error": "authority_unavailable"}
    if canonical_service is None:
        canonical_service = _canonical_service_for_runtime(runtime)
    if name not in TOOL_NAMES:
        return {"ok": False, "error": "unknown_tool", "tool": name}
    if name == "get_task_context":
        try:
            request = parse_task_context_request(args)
        except Exception:
            return invalid_arguments_response(
                trace_id=authority.trace_id, live_data=runtime.live_data
            ).model_dump(mode="json", exclude_none=True)
        return (
            await runtime.get_task_context(authority=authority, request=request)
        ).model_dump(mode="json", exclude_none=True)
    if name == "create_handoff_bundle":
        return create_handoff_bundle(arguments or {})
    if name in {"retrieve_context", "get_related_work"}:
        allowed = {"query", "source_allowlist", "provider_filters"}
        if local_compatibility:
            allowed.add("workspace_id")
        unknown = sorted(set(args) - allowed)
        if unknown:
            return {"ok": False, "error": "unknown_arguments", "fields": unknown}
        if "query" not in args or (local_compatibility and "workspace_id" not in args):
            return {"ok": False, "error": "missing_required_arguments"}
        if (
            "workspace_id" in args
            and str(args["workspace_id"]) != authority.workspace_id
        ):
            return {"ok": False, "error": "workspace_scope_mismatch"}
        response = await runtime.retrieve(
            authority=authority,
            query=str(args["query"]),
            source_allowlist=list(args.get("source_allowlist", [])),
            provider_filters=list(args.get("provider_filters", [])),
            related=name == "get_related_work",
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
        allowed = {
            "query",
            "evidence_pack_id",
            "task_hints",
            "source_allowlist",
            "provider_filters",
        }
        if local_compatibility:
            allowed.add("workspace_id")
        unknown = sorted(set(args) - allowed)
        if unknown:
            return {"ok": False, "error": "unknown_arguments", "fields": unknown}
        if "query" not in args and "evidence_pack_id" not in args:
            return {"ok": False, "error": "missing_required_arguments"}
        if (
            "workspace_id" in args
            and str(args["workspace_id"]) != authority.workspace_id
        ):
            return {"ok": False, "error": "workspace_scope_mismatch"}
        gate_response = await runtime.check_gate(
            authority=authority,
            query=str(args["query"]) if "query" in args else None,
            evidence_pack_id=(
                str(args["evidence_pack_id"]) if "evidence_pack_id" in args else None
            ),
            task_hints=dict(args.get("task_hints", {})),
            source_allowlist=list(args.get("source_allowlist", [])),
            provider_filters=list(args.get("provider_filters", [])),
        )
        if gate_response is None:
            return {"ok": False, "tool": name, "error": "context_gate_unavailable"}
        return {
            "ok": gate_response.ok,
            "tool": name,
            "context_gate_result_id": gate_response.context_gate_result_id,
            "status": gate_response.status,
            "text": gate_response.text,
            "result": gate_response.result,
            **({"error": gate_response.error} if gate_response.error else {}),
        }
    if name == "propose_canonical_decision":
        allowed = {
            "evidence_pack_id",
            "context_gate_result_id",
            "scope_type",
            "scope_ref",
            "title",
            "decision_text",
        }
        if local_compatibility:
            allowed.add("workspace_id")
        unknown = sorted(set(args) - allowed)
        if unknown:
            return {"ok": False, "error": "unknown_arguments", "fields": unknown}
        if "evidence_pack_id" not in args and "context_gate_result_id" not in args:
            return {"ok": False, "error": "missing_required_arguments"}
        if (
            local_compatibility
            and "workspace_id" in args
            and str(args["workspace_id"]) != authority.workspace_id
        ):
            return {"ok": False, "error": "workspace_scope_mismatch"}
        canonical_response = canonical_service.propose_canonical_decision(
            workspace_id=authority.workspace_id,
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
            actor_id=authority.actor_id,
        )
        return {
            "ok": canonical_response.ok,
            "tool": name,
            "text": canonical_response.text,
            "result": canonical_response.result,
            **({"error": canonical_response.error} if canonical_response.error else {}),
        }
    if name == "approve_canonical_decision":
        args = arguments or {}
        allowed = {
            "decision_id",
            "action",
            "final_text",
            "rationale",
            "supersedes_decision_id",
        }
        unknown = sorted(set(args) - allowed)
        if unknown:
            return {"ok": False, "error": "unknown_arguments", "fields": unknown}
        if "decision_id" not in args or "action" not in args:
            return {"ok": False, "error": "missing_required_arguments"}
        if authority.actor_id is None:
            return {"ok": False, "error": "human_actor_required"}
        try:
            decision = canonical_service.decisions.get_by_id(str(args["decision_id"]))
        except KeyError:
            return {"ok": False, "error": "unknown_decision_id"}
        if decision.workspace_id != authority.workspace_id:
            return {"ok": False, "error": "workspace_scope_mismatch"}
        canonical_response = await canonical_service.approve_canonical_decision(
            decision_id=str(args["decision_id"]),
            action=str(args["action"]),
            actor_id=authority.actor_id,
            final_text=str(args["final_text"]) if "final_text" in args else None,
            rationale=str(args["rationale"]) if "rationale" in args else None,
            supersedes_decision_id=(
                str(args["supersedes_decision_id"])
                if "supersedes_decision_id" in args
                else None
            ),
        )
        return {
            "ok": canonical_response.ok,
            "tool": name,
            "text": canonical_response.text,
            "result": canonical_response.result,
            **({"error": canonical_response.error} if canonical_response.error else {}),
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
    for name in ("retrieve_context", "get_related_work"):
        tool = next(item for item in definitions if item["name"] == name)
        tool["inputSchema"] = {
            "type": "object",
            "additionalProperties": False,
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "source_allowlist": {"type": "array", "items": {"type": "string"}},
                "provider_filters": {"type": "array", "items": {"type": "string"}},
            },
        }
    task_context = next(
        item for item in definitions if item["name"] == "get_task_context"
    )
    task_context.update(
        {
            "description": (
                "Pull bounded, permission-filtered company context for a task, "
                "including citations, source coverage, conflicts, and freshness. "
                "Cortex does not control or resume agent sessions."
            ),
            "inputSchema": TaskContextRequest.model_json_schema(),
        }
    )
    gate = next(item for item in definitions if item["name"] == "check_context_gate")
    gate["inputSchema"] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "evidence_pack_id": {"type": "string", "minLength": 1},
            "task_hints": {"type": "object"},
            "source_allowlist": {"type": "array", "items": {"type": "string"}},
            "provider_filters": {"type": "array", "items": {"type": "string"}},
        },
        "anyOf": [{"required": ["query"]}, {"required": ["evidence_pack_id"]}],
    }
    proposal = next(
        item for item in definitions if item["name"] == "propose_canonical_decision"
    )
    proposal["inputSchema"] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "evidence_pack_id": {"type": "string", "minLength": 1},
            "context_gate_result_id": {"type": "string", "minLength": 1},
            "scope_type": {"type": "string", "minLength": 1},
            "scope_ref": {"type": "string", "minLength": 1},
            "title": {"type": "string", "minLength": 1},
            "decision_text": {"type": "string", "minLength": 1},
        },
        "anyOf": [
            {"required": ["evidence_pack_id"]},
            {"required": ["context_gate_result_id"]},
        ],
    }
    approval = next(
        item for item in definitions if item["name"] == "approve_canonical_decision"
    )
    approval["inputSchema"] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["decision_id", "action"],
        "properties": {
            "decision_id": {"type": "string", "minLength": 1},
            "action": {"type": "string", "enum": sorted(APPROVAL_ACTIONS)},
            "final_text": {"type": "string", "minLength": 1},
            "rationale": {"type": "string", "minLength": 1},
            "supersedes_decision_id": {"type": "string", "minLength": 1},
        },
    }
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


async def handle_json_rpc_message(
    message: object, *, server: McpServer | None = None, fixture_mode: bool = False
) -> dict[str, object] | None:
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
        result = {
            "tools": server.tool_definitions()
            if server is not None
            else list_tool_definitions()
        }
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
        # A transport host must resolve authority before dispatch.  The only
        # fallback is an explicit fixed-scope fixture for local tests.
        active_server = server or (create_fixture_server() if fixture_mode else None)
        if active_server is None and name != "create_handoff_bundle":
            response = {"ok": False, "error": "authority_unavailable"}
        elif active_server is None:
            response = create_handoff_bundle(dict(arguments))
        else:
            response = await active_server.call_tool(name, dict(arguments))
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


async def serve_stdio(
    *, server: McpServer | None = None, fixture_mode: bool = False
) -> None:
    """Serve JSON-RPC using authority injected by the embedding host.

    ``fixture_mode`` is deliberately opt-in and has a fixed ``ws_1`` scope.
    """
    for line in sys.stdin:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response: dict[str, object] | None = _json_rpc_error(
                None, -32700, "Parse error"
            )
        else:
            response = await handle_json_rpc_message(
                message, server=server, fixture_mode=fixture_mode
            )
        if response is not None:
            sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
            sys.stdout.flush()


def main() -> None:
    """Console-script entry point for the local MCP stdio server."""
    from cortex.mcp.proxy import (
        ApiTaskContextProxy,
        LocalMcpProxyConfig,
        McpProxyConfigurationError,
        UnavailableTaskContextProxy,
    )

    mode = os.environ.get("CORTEX_MCP_MODE", "").strip().lower()
    if mode == "fixture":
        asyncio.run(serve_stdio(server=create_fixture_server()))
        return
    if mode == "proxy":
        try:
            proxy: TaskContextProxy = ApiTaskContextProxy(
                LocalMcpProxyConfig.from_environment()
            )
        except McpProxyConfigurationError:
            proxy = UnavailableTaskContextProxy()
        asyncio.run(
            serve_stdio(server=create_local_proxy_server(task_context_proxy=proxy))
        )
        return
    asyncio.run(serve_stdio())


if __name__ == "__main__":
    main()
