from cortex.dev.workbench import DevWorkbenchService


def test_cor_123_gate_blocks_with_actionable_reason() -> None:
    service = DevWorkbenchService()
    service.seed()
    result = service.query("COR-123")
    gate = result["gate_result"]

    assert gate["status"] == "block"
    assert gate["risk_category"] == "architecture_conflict"
    assert any("conflict" in reason for reason in gate["reasons"])
    assert gate["required_actions"]
