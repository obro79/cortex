from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime

from cortex.connectors.slack.service import create_slack_connector_services


def signed_headers(body: dict[str, object], secret: str) -> dict[str, str]:
    timestamp = str(int(datetime.now(UTC).timestamp()))
    raw = json.dumps(body, separators=(",", ":")).encode()
    base = b"v0:" + timestamp.encode() + b":" + raw
    signature = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return {
        "x-slack-request-timestamp": timestamp,
        "x-slack-signature": signature,
        "content-type": "application/json",
    }


async def installed_selected_services():
    services = create_slack_connector_services(signing_secret="test-secret")
    started = services.oauth.start_install(workspace_id="ws_1", actor_id="human_1")
    completed = await services.oauth.complete_install(
        code="code_123",
        state=str(started["state"]),
    )
    install_id = completed["installation"]["id"]
    selected = await services.sources.select_channels(
        workspace_id="ws_1",
        oauth_installation_id=install_id,
        channels=[{"id": "C123", "name": "private-roadmap"}],
    )
    return services, completed, selected
