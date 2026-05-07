from cortex.mcp.server import call_tool


async def test_approve_canonical_decision_tool_requires_human_actor() -> None:
    retrieval = await call_tool(
        "retrieve_context", {"workspace_id": "ws_1", "query": "session migration"}
    )
    proposal = await call_tool(
        "propose_canonical_decision",
        {
            "workspace_id": "ws_1",
            "evidence_pack_id": retrieval["evidence_pack_id"],
            "decision_text": "Postgres is canonical for session storage.",
        },
    )

    response = await call_tool(
        "approve_canonical_decision",
        {
            "decision_id": proposal["result"]["id"],
            "action": "approve",
            "actor_id": "agent_1",
        },
    )

    assert response["ok"] is False
    assert response["error"] == "human_actor_required"


async def test_approve_canonical_decision_tool_success_and_retrieval_priority() -> None:
    retrieval = await call_tool(
        "retrieve_context", {"workspace_id": "ws_1", "query": "session migration"}
    )
    proposal = await call_tool(
        "propose_canonical_decision",
        {
            "workspace_id": "ws_1",
            "evidence_pack_id": retrieval["evidence_pack_id"],
            "decision_text": "Postgres is canonical for session storage.",
        },
    )

    approval = await call_tool(
        "approve_canonical_decision",
        {
            "decision_id": proposal["result"]["id"],
            "action": "approve",
            "actor_id": "human_1",
        },
    )
    future = await call_tool(
        "retrieve_context", {"workspace_id": "ws_1", "query": "session storage"}
    )

    assert approval["ok"] is True
    assert approval["result"]["decision"]["status"] == "approved"
    assert approval["result"]["approval_record"]["actor_id"] == "human_1"
    assert "Postgres is canonical" in future["text"]
