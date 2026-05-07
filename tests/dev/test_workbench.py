from cortex.dev.workbench import DevWorkbenchService


def test_workbench_renders_empty_state() -> None:
    service = DevWorkbenchService()
    html = service.render_workbench_html()

    assert "Cortex Dev Workbench" in html
    assert "No fixtures seeded yet" in html
    assert "Seed Fixtures" in html
    assert "Run Pipeline" in html
    assert "Query COR-123" in html
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
