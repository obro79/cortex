from cortex.connectors.slack.oauth import REQUIRED_SLACK_SCOPES, SlackTokenResponse
from cortex.connectors.slack.service import create_slack_connector_services
from cortex.contracts.enums import OAuthInstallationStatus


class MissingScopeClient:
    async def exchange_code(self, code: str) -> SlackTokenResponse:
        return SlackTokenResponse(
            access_token="test-token-material",
            team_id="T_MISSING",
            scopes={"channels:read"},
        )


async def test_oauth_state_required_and_token_stored_by_secret_ref() -> None:
    services = create_slack_connector_services()
    start = services.oauth.start_install(workspace_id="ws_1", actor_id="human_1")

    invalid = await services.oauth.complete_install(code="code_123", state="bad")
    complete = await services.oauth.complete_install(
        code="code_123",
        state=str(start["state"]),
    )

    assert invalid == {"ok": False, "error": "invalid_oauth_state"}
    assert complete["ok"] is True
    assert complete["installation"]["status"] == OAuthInstallationStatus.ACTIVE
    assert set(complete["installation"]["scopes_json"]["scopes"]) == set(
        REQUIRED_SLACK_SCOPES
    )
    assert "xoxb" not in str(complete)
    assert complete["secret_ref"]["external_secret_id"].startswith("local-secret:")


def test_oauth_start_returns_authorization_url_when_configured() -> None:
    services = create_slack_connector_services(
        client_id="client-id",
        redirect_uri="http://localhost/callback",
    )

    start = services.oauth.start_install(workspace_id="ws_1")

    authorization_url = str(start["authorization_url"])
    assert authorization_url.startswith("https://slack.com/oauth/v2/authorize?")
    assert "client_id=client-id" in authorization_url
    assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in authorization_url
    assert str(start["state"]) in authorization_url


async def test_missing_required_scopes_marks_install_unhealthy() -> None:
    services = create_slack_connector_services()
    services.oauth.client = MissingScopeClient()
    start = services.oauth.start_install(workspace_id="ws_1")

    complete = await services.oauth.complete_install(
        code="code_123",
        state=str(start["state"]),
    )

    assert complete["ok"] is False
    assert complete["error"] == "missing_required_scopes"
    assert complete["installation"]["status"] == OAuthInstallationStatus.NEEDS_REAUTH
    assert (
        "channels:history" in complete["installation"]["health_json"]["missing_scopes"]
    )
