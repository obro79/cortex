from cortex.dev.workbench import DevWorkbenchService


def test_workbench_renders_empty_state() -> None:
    service = DevWorkbenchService()
    html = service.render_workbench_html()

    assert "Cortex Dev Workbench" in html
    assert "No fixtures seeded yet" in html
    assert "Seed Fixtures" in html
    assert "Run Pipeline" in html
    assert "Load COR-123 context" in html
    assert "freeform search unavailable" in html
    assert "not_run" in html


async def test_workbench_renders_completed_state() -> None:
    service = DevWorkbenchService()
    service.seed()
    await service.run_pipeline()
    service.query("COR-123")
    service.run_evals()
    html = service.render_workbench_html()

    assert "run-cor-123-001" in html
    assert "kafka_event" in html
    assert "ep-cor-123" in html
    assert "block" in html
    assert "recall_at_k" in html


async def test_pipeline_run_updates_latest_gate_without_a_retrieval_query() -> None:
    service = DevWorkbenchService()
    service.seed()

    await service.run_pipeline()

    assert service.state_summary()["latest_gate_status"] == "block"
