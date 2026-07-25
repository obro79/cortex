from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.config import Settings


def test_fixture_evidence_route_is_available_only_with_the_local_workbench() -> None:
    disabled = TestClient(create_app(Settings(cortex_dev_workbench_enabled=False)))
    assert disabled.get("/demo/evidence").status_code == 404

    enabled = TestClient(create_app(Settings(cortex_dev_workbench_enabled=True)))
    response = enabled.get("/demo/evidence")

    assert response.status_code == 200
    body = response.json()
    assert body["live_data"] is False
    assert body["corpus"]["source_object_count"] == 10
    assert body["corpus"]["source_file_count"] == 3
    assert body["pipeline"]["stage_count"] == 10
    assert body["decision"]["gate_status"] == "block"
    assert "https://" not in response.text
    assert "Postgres is the approved" not in response.text
