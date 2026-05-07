from cortex.dev.workbench import DevWorkbenchService


def test_eval_runner_reports_required_metrics() -> None:
    service = DevWorkbenchService()
    result = service.run_evals()

    assert result["status"] == "passed"
    assert set(result["metrics"]) == {
        "recall_at_k",
        "mrr",
        "citation_accuracy",
        "conflict_detection",
        "gate_accuracy",
        "latency_ms",
    }
    assert result["metrics"]["recall_at_k"] == 1.0
    assert result["metrics"]["gate_accuracy"] == 1.0
