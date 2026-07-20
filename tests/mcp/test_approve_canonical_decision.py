from cortex.mcp.server import McpServer
from cortex.runtime import CortexAuthority, create_local_runtime


def _server(*, actor_id: str | None) -> McpServer:
    return McpServer(
        runtime=create_local_runtime(),
        authority=CortexAuthority(
            workspace_id="ws_1", actor_id=actor_id, trace_id="test-trace"
        ),
    )


async def test_approve_canonical_decision_tool_requires_human_actor() -> None:
    server = _server(actor_id=None)
    retrieval = await server.call_tool(
        "retrieve_context", {"query": "session migration"}
    )
    proposal = await server.call_tool(
        "propose_canonical_decision",
        {
            "evidence_pack_id": retrieval["evidence_pack_id"],
            "decision_text": "Postgres is canonical for session storage.",
        },
    )

    response = await server.call_tool(
        "approve_canonical_decision",
        {
            "decision_id": proposal["result"]["id"],
            "action": "approve",
        },
    )

    assert response["ok"] is False
    assert response["error"] == "human_actor_required"


async def test_approve_canonical_decision_tool_success_and_retrieval_priority() -> None:
    server = _server(actor_id="human_1")
    retrieval = await server.call_tool(
        "retrieve_context", {"query": "session migration"}
    )
    proposal = await server.call_tool(
        "propose_canonical_decision",
        {
            "evidence_pack_id": retrieval["evidence_pack_id"],
            "decision_text": "Postgres is canonical for session storage.",
        },
    )

    approval = await server.call_tool(
        "approve_canonical_decision",
        {
            "decision_id": proposal["result"]["id"],
            "action": "approve",
        },
    )
    future = await server.call_tool(
        "retrieve_context", {"query": "session storage"}
    )

    assert approval["ok"] is True
    assert approval["result"]["decision"]["status"] == "approved"
    assert approval["result"]["approval_record"]["actor_id"] == "human_1"
    assert "Postgres is canonical" in future["text"]
