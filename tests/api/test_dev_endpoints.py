from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.config import Settings


def enabled_client() -> TestClient:
    return TestClient(create_app(Settings(cortex_dev_workbench_enabled=True)))


def test_fixture_seed_reset_endpoints() -> None:
    client = enabled_client()
    seed = client.post("/dev/fixtures/seed")
    assert seed.status_code == 200
    assert "linear-issue-COR-123" in seed.json()["fixture_ids"]
    assert seed.json()["counts"]["source_objects"] == 6

    seed_again = client.post("/dev/fixtures/seed")
    assert seed_again.json()["counts"] == seed.json()["counts"]

    reset = client.post("/dev/fixtures/reset")
    assert reset.status_code == 200
    assert reset.json()["state"]["fixture_counts"]["source_objects"] == 0


def test_pipeline_query_evidence_and_eval_endpoints() -> None:
    client = enabled_client()
    seed = client.post("/dev/fixtures/seed")
    assert seed.status_code == 200

    run = client.post("/dev/pipeline/run")
    assert run.status_code == 200
    run_body = run.json()
    assert run_body["run_id"] == "run-cor-123-001"
    assert [stage["stage"] for stage in run_body["stages"]] == [
        "seed",
        "ingest",
        "kafka_event",
        "normalize",
        "chunk_ocr",
        "embed",
        "index",
        "link",
        "retrieve",
        "gate",
    ]

    run_read = client.get(f"/dev/pipeline/runs/{run_body['run_id']}")
    assert run_read.status_code == 200
    assert run_read.json()["trace_id"] == "trace-run-cor-123-001"

    query = client.post(
        "/dev/retrieval/query",
        json={"query": "What constrains COR-123 session work?"},
    )
    assert query.status_code == 200
    query_body = query.json()
    assert query_body["gate_status"] == "block"
    assert "repo-doc-session-storage" in query_body["expected_sources"]

    evidence = client.get(f"/dev/evidence-packs/{query_body['evidence_pack_id']}")
    assert evidence.status_code == 200
    assert evidence.json()["gate_result"]["risk_category"] == "architecture_conflict"

    evals = client.post("/dev/evals/run")
    assert evals.status_code == 200
    assert evals.json()["status"] == "passed"


def test_missing_records_return_404() -> None:
    client = enabled_client()
    assert client.get("/dev/pipeline/runs/missing").status_code == 404
    assert client.get("/dev/evidence-packs/missing").status_code == 404


def test_run_and_query_require_seeded_fixtures() -> None:
    client = enabled_client()

    run = client.post("/dev/pipeline/run")
    assert run.status_code == 409
    assert run.json()["detail"]["code"] == "fixtures_not_seeded"

    query = client.post("/dev/retrieval/query", json={"query": "COR-123"})
    assert query.status_code == 409
    assert query.json()["detail"]["code"] == "fixtures_not_seeded"
