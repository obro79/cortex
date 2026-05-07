from __future__ import annotations

from dataclasses import dataclass
from secrets import token_urlsafe

from cortex.contracts.enums import OAuthInstallationStatus

from .repositories import (
    InMemoryOAuthInstallationRepository,
    InMemorySecretRefRepository,
)

REQUIRED_SLACK_SCOPES = frozenset(
    {"channels:history", "channels:read", "files:read", "links:read"}
)


@dataclass(frozen=True)
class SlackTokenResponse:
    access_token: str
    team_id: str
    scopes: set[str]
    enterprise_id: str | None = None
    bot_user_id: str | None = None


class SlackOAuthClient:
    async def exchange_code(self, code: str) -> SlackTokenResponse:
        return SlackTokenResponse(
            access_token=f"slack-token-material-{code[-6:]}",
            team_id="T_TEST",
            scopes=set(REQUIRED_SLACK_SCOPES),
            bot_user_id="B_TEST",
        )


class SlackOAuthService:
    def __init__(
        self,
        *,
        secrets: InMemorySecretRefRepository,
        installations: InMemoryOAuthInstallationRepository,
        client: SlackOAuthClient | None = None,
    ) -> None:
        self.secrets = secrets
        self.installations = installations
        self.client = client or SlackOAuthClient()
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
        }

    async def complete_install(self, *, code: str, state: str) -> dict[str, object]:
        state_record = self._states.pop(state, None)
        if state_record is None:
            return {"ok": False, "error": "invalid_oauth_state"}
        workspace_id, actor_id = state_record
        token = await self.client.exchange_code(code)
        missing = sorted(REQUIRED_SLACK_SCOPES - token.scopes)
        secret_ref = self.secrets.create_for_token(
            workspace_id=workspace_id,
            provider="slack",
            token=token.access_token,
        )
        status = (
            OAuthInstallationStatus.NEEDS_REAUTH
            if missing
            else OAuthInstallationStatus.ACTIVE
        )
        install = self.installations.upsert_active(
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
        return {
            "ok": not missing,
            "installation": install.model_dump(mode="json"),
            "secret_ref": secret_ref.model_dump(mode="json"),
            **({"error": "missing_required_scopes"} if missing else {}),
        }
