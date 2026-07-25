from cortex.mcp.server import call_tool


async def test_check_context_gate_tool_shape_and_errors() -> None:
    missing = await call_tool("check_context_gate", {"workspace_id": "ws_1"})
    unknown = await call_tool(
        "check_context_gate",
        {"workspace_id": "ws_1", "query": "session", "extra": True},
    )
    response = await call_tool(
        "check_context_gate",
        {"workspace_id": "ws_1", "query": "session migration"},
    )

    assert missing == {"ok": False, "error": "missing_required_arguments"}
    assert unknown["error"] == "unknown_arguments"
    assert response["ok"] is True
    assert response["tool"] == "check_context_gate"
    assert response["context_gate_result_id"].startswith("gate_")
    assert response["status"] in {"allow", "warn", "block"}
    assert "text" in response


async def test_check_context_gate_can_evaluate_existing_evidence_pack_id() -> None:
    retrieval = await call_tool(
        "retrieve_context",
        {"workspace_id": "ws_1", "query": "button label"},
    )
    response = await call_tool(
        "check_context_gate",
        {
            "workspace_id": "ws_1",
            "query": "button label",
            "evidence_pack_id": retrieval["evidence_pack_id"],
        },
    )

    assert response["ok"] is True
    assert response["result"]["evidence_pack_id"] == retrieval["evidence_pack_id"]
