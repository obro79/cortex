import json

import pytest

from cortex.workers.provider_acls import (
    provider_acl_principal_mappings_from_json,
    provider_acl_refresh_targets_from_json,
)


def test_provider_acl_worker_parses_refresh_targets_without_tokens() -> None:
    targets = provider_acl_refresh_targets_from_json(
        json.dumps(
            [
                {
                    "workspace_id": "ws_1",
                    "provider": "github",
                    "resource_type": "github_repository",
                    "repository_id": "42",
                    "owner": "acme",
                    "repo": "app",
                    "token_env": "GITHUB_INSTALLATION_TOKEN",
                }
            ]
        )
    )

    assert len(targets) == 1
    assert targets[0].workspace_id == "ws_1"
    assert targets[0].external_id == "42"
    assert targets[0].token_env == "GITHUB_INSTALLATION_TOKEN"


def test_provider_acl_worker_rejects_inline_secret_targets() -> None:
    with pytest.raises(ValueError, match="token_env"):
        provider_acl_refresh_targets_from_json(
            json.dumps(
                [
                    {
                        "workspace_id": "ws_1",
                        "provider": "slack",
                        "resource_type": "slack_channel",
                        "channel_id": "C123",
                        "access_token": "xoxb_secret",
                    }
                ]
            )
        )


def test_provider_acl_worker_parses_principal_mappings() -> None:
    mappings = provider_acl_principal_mappings_from_json(
        json.dumps(
            {
                "mappings": [
                    {
                        "workspace_id": "ws_1",
                        "user_id": "usr_1",
                        "provider": "slack",
                        "principal_type": "user",
                        "external_id": "U1",
                    }
                ]
            }
        )
    )

    assert len(mappings) == 1
    assert mappings[0].match_method == "admin_configured"
