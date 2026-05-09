from __future__ import annotations

from dataclasses import dataclass
from secrets import token_urlsafe
from typing import Any, Protocol
from urllib.parse import urlencode

from cortex.contracts.enums import OAuthInstallationStatus
from cortex.utils.asyncio import maybe_await

from .client import SlackHttpClient, SlackOAuthError

REQUIRED_SLACK_SCOPES = frozenset(
    {
        "channels:history",
        "channels:read",
        "files:read",
        "groups:history",
        "groups:read",
        "links:read",
        "team:read",
    }
)


@dataclass(frozen=True)
class SlackTokenResponse:
    access_token: str
    team_id: str
    scopes: set[str]
    enterprise_id: str | None = None
    bot_user_id: str | None = None


class SlackOAuthClient(Protocol):
    async def exchange_code(self, code: str) -> SlackTokenResponse: ...


class FakeSlackOAuthClient:
    async def exchange_code(self, code: str) -> SlackTokenResponse:
        return SlackTokenResponse(
            access_token=f"slack-token-material-{code[-6:]}",
            team_id="T_TEST",
            scopes=set(REQUIRED_SLACK_SCOPES),
            bot_user_id="B_TEST",
        )


class RealSlackOAuthClient:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        http: SlackHttpClient | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.http = http or SlackHttpClient()

    async def exchange_code(self, code: str) -> SlackTokenResponse:
        payload = await self.http.oauth_access(
            client_id=self.client_id,
            client_secret=self.client_secret,
            code=code,
            redirect_uri=self.redirect_uri,
        )
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise SlackOAuthError("missing_access_token")
        team = payload.get("team")
        team_id = (
            str(team.get("id"))
            if isinstance(team, dict) and isinstance(team.get("id"), str)
            else ""
        )
        if not team_id:
            raise SlackOAuthError("missing_team_id")
        enterprise = payload.get("enterprise")
        scope_value = payload.get("scope", "")
        return SlackTokenResponse(
            access_token=token,
            team_id=team_id,
            scopes={scope.strip() for scope in str(scope_value).split(",") if scope},
            enterprise_id=(
                str(enterprise.get("id"))
                if isinstance(enterprise, dict) and enterprise.get("id")
                else None
            ),
            bot_user_id=str(payload["bot_user_id"])
            if isinstance(payload.get("bot_user_id"), str)
            else None,
        )


class SlackOAuthService:
    def __init__(
        self,
        *,
        secrets: Any,
        installations: Any,
        client: SlackOAuthClient | None = None,
        client_id: str = "",
        redirect_uri: str = "",
    ) -> None:
        self.secrets = secrets
        self.installations = installations
        self.client = client or FakeSlackOAuthClient()
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self._states: dict[str, tuple[str, str | None]] = {}

    def start_install(
        self, *, workspace_id: str, actor_id: str | None = None
    ) -> dict[str, object]:
        state = token_urlsafe(24)
        self._states[state] = (workspace_id, actor_id)
        return {
            "ok": True,
            "provider": "slack",
            "state": state,
            "required_scopes": sorted(REQUIRED_SLACK_SCOPES),
            "authorization_url": self._authorization_url(state),
        }

    async def complete_install(self, *, code: str, state: str) -> dict[str, object]:
        state_record = self._states.pop(state, None)
        if state_record is None:
            return {"ok": False, "error": "invalid_oauth_state"}
        workspace_id, actor_id = state_record
        try:
            token = await self.client.exchange_code(code)
        except SlackOAuthError as exc:
            return {"ok": False, "error": "oauth_exchange_failed", "reason": str(exc)}
        missing = sorted(REQUIRED_SLACK_SCOPES - token.scopes)
        secret_ref = await maybe_await(
            self.secrets.create_for_token(
                workspace_id=workspace_id,
                provider="slack",
                token=token.access_token,
            )
        )
        status = (
            OAuthInstallationStatus.NEEDS_REAUTH
            if missing
            else OAuthInstallationStatus.ACTIVE
        )
        install = await maybe_await(
            self.installations.upsert_active(
                workspace_id=workspace_id,
                provider_workspace_id=token.team_id,
                secret_ref_id=secret_ref.id,
                scopes=token.scopes,
                status=status,
                health_json={"missing_scopes": missing, "ok": not missing},
                enterprise_id=token.enterprise_id,
                bot_user_id=token.bot_user_id,
                installing_actor_id=actor_id,
                provider_metadata_json={"team_id": token.team_id},
            )
        )
        return {
            "ok": not missing,
            "installation": install.model_dump(mode="json"),
            "secret_ref": secret_ref.model_dump(mode="json"),
            **({"error": "missing_required_scopes"} if missing else {}),
        }

    def _authorization_url(self, state: str) -> str | None:
        if not self.client_id or not self.redirect_uri:
            return None
        query = urlencode(
            {
                "client_id": self.client_id,
                "scope": ",".join(sorted(REQUIRED_SLACK_SCOPES)),
                "redirect_uri": self.redirect_uri,
                "state": state,
            }
        )
        return f"https://slack.com/oauth/v2/authorize?{query}"
