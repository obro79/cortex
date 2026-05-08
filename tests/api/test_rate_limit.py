from __future__ import annotations

from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.config import Settings


def test_api_rate_limit_returns_retry_metadata() -> None:
    client = TestClient(
        create_app(
            Settings(
                cortex_dev_workbench_enabled=True,
                cortex_api_rate_limit_enabled=True,
                cortex_api_rate_limit_requests=1,
                cortex_api_rate_limit_window_seconds=30,
            )
        )
    )

    allowed = client.get(
        "/dev/workbench",
        headers={"X-Workspace-ID": "workspace-1", "X-User-ID": "user-1"},
    )
    denied = client.get(
        "/dev/workbench",
        headers={"X-Workspace-ID": "workspace-1", "X-User-ID": "user-1"},
    )

    assert allowed.status_code == 200
    assert allowed.headers["X-RateLimit-Limit"] == "1"
    assert allowed.headers["X-RateLimit-Remaining"] == "0"
    assert denied.status_code == 429
    assert denied.headers["Retry-After"] == "30"
    assert denied.json() == {
        "detail": "rate limit exceeded",
        "code": "rate_limit_exceeded",
        "retry_after_seconds": 30,
    }


def test_api_rate_limit_is_per_workspace_and_user() -> None:
    client = TestClient(
        create_app(
            Settings(
                cortex_dev_workbench_enabled=True,
                cortex_api_rate_limit_enabled=True,
                cortex_api_rate_limit_requests=1,
            )
        )
    )

    first_user = {"X-Workspace-ID": "workspace-1", "X-User-ID": "user-1"}
    second_user = {"X-Workspace-ID": "workspace-1", "X-User-ID": "user-2"}

    assert client.get("/dev/workbench", headers=first_user).status_code == 200
    assert client.get("/dev/workbench", headers=first_user).status_code == 429
    assert client.get("/dev/workbench", headers=second_user).status_code == 200


def test_health_routes_are_not_rate_limited() -> None:
    client = TestClient(
        create_app(
            Settings(
                cortex_api_rate_limit_enabled=True,
                cortex_api_rate_limit_requests=1,
            )
        )
    )

    assert client.get("/health/live").status_code == 200
    assert client.get("/health/live").status_code == 200
