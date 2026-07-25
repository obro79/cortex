from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.config import Settings


def test_case_study_route_is_public_and_redacted() -> None:
    client = TestClient(
        create_app(
            Settings(
                cortex_dev_workbench_enabled=False,
                cortex_ui_enabled=False,
            )
        )
    )

    response = client.get("/case-study")

    assert response.status_code == 200
    assert "Evidence-aware knowledge infrastructure" in response.text
    assert "10-record deterministic demo fixture" in response.text
    assert "not live provider data" in response.text
    assert "allow/warn/block" in response.text
    assert "portable, opt-in" in response.text
    assert "xoxb" not in response.text
