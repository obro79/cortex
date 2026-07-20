from cortex.mcp.server import McpServer
from cortex.runtime import CortexAuthority, create_local_runtime


async def test_injected_mcp_authority_ignores_client_workspace_claim() -> None:
    server = McpServer(
        runtime=create_local_runtime(),
        authority=CortexAuthority(
            workspace_id="ws_1", actor_id="user_1", trace_id="trace_1"
        ),
    )

    denied = await server.call_tool(
        "retrieve_context", {"workspace_id": "other", "query": "session"}
    )
    allowed = await server.call_tool("retrieve_context", {"query": "session"})

    assert denied["error"] == "unknown_arguments"
    assert allowed["ok"] is True


async def test_canonical_tools_bind_authority_and_runtime_evidence() -> None:
    server = McpServer(
        runtime=create_local_runtime(),
        authority=CortexAuthority(
            workspace_id="ws_1", actor_id="human_host", trace_id="trace_1"
        ),
    )

    retrieval = await server.call_tool("retrieve_context", {"query": "session"})
    spoofed = await server.call_tool(
        "propose_canonical_decision",
        {
            "workspace_id": "other",
            "evidence_pack_id": retrieval["evidence_pack_id"],
        },
    )
    proposal = await server.call_tool(
        "propose_canonical_decision",
        {"evidence_pack_id": retrieval["evidence_pack_id"]},
    )
    approval = await server.call_tool(
        "approve_canonical_decision",
        {"decision_id": proposal["result"]["id"], "action": "approve"},
    )

    assert spoofed == {
        "ok": False,
        "error": "unknown_arguments",
        "fields": ["workspace_id"],
    }
    assert proposal["ok"] is True
    assert proposal["result"]["workspace_id"] == "ws_1"
    assert approval["ok"] is True
    assert approval["result"]["approval_record"]["actor_id"] == "human_host"
