from cortex.mcp.server import call_tool


async def test_propose_canonical_decision_tool_success_and_errors() -> None:
    missing = await call_tool("propose_canonical_decision", {"workspace_id": "ws_1"})
    retrieval = await call_tool(
        "retrieve_context", {"workspace_id": "ws_1", "query": "session migration"}
    )
    proposal = await call_tool(
        "propose_canonical_decision",
        {
            "workspace_id": "ws_1",
            "evidence_pack_id": retrieval["evidence_pack_id"],
            "scope_type": "linear_issue",
            "scope_ref": "COR-123",
            "title": "Session storage canonical decision",
            "decision_text": "Postgres is canonical for session storage.",
        },
    )

    assert missing == {"ok": False, "error": "missing_required_arguments"}
    assert proposal["ok"] is True
    assert proposal["result"]["status"] == "needs_review"
    assert proposal["result"]["title"] == "Session storage canonical decision"
