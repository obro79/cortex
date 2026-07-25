"""Report Slack/GitHub demo prerequisites without contacting either provider."""

from __future__ import annotations

import argparse
import json
import os
from typing import Final

SLACK_ENV: Final = (
    "SLACK_CLIENT_ID",
    "SLACK_CLIENT_SECRET",
    "SLACK_SIGNING_SECRET",
    "SLACK_REDIRECT_URI",
)
GITHUB_REQUIRED_ENV: Final = ("GITHUB_WEBHOOK_SECRET",)
GITHUB_CREDENTIAL_ALTERNATIVES: Final = (
    "GITHUB_INSTALLATION_TOKEN",
    "GITHUB_APP_ID",
    "GITHUB_PRIVATE_KEY",
)


def _presence(names: tuple[str, ...]) -> dict[str, bool]:
    return {name: bool(os.getenv(name)) for name in names}


def preflight() -> dict[str, object]:
    """Return only presence/status values; secrets are never returned or used."""
    slack = _presence(SLACK_ENV)
    github_required = _presence(GITHUB_REQUIRED_ENV)
    github_credentials = _presence(GITHUB_CREDENTIAL_ALTERNATIVES)
    github_auth_ready = github_credentials["GITHUB_INSTALLATION_TOKEN"] or (
        github_credentials["GITHUB_APP_ID"] and github_credentials["GITHUB_PRIVATE_KEY"]
    )
    return {
        "ok": all(slack.values())
        and all(github_required.values())
        and github_auth_ready,
        "mode": "preflight",
        "network_access": False,
        "provider_calls": False,
        "providers": {
            "slack": {"ready": all(slack.values()), "environment": slack},
            "github": {
                "ready": all(github_required.values()) and github_auth_ready,
                "environment": {**github_required, **github_credentials},
                "auth": "installation_token_or_app_credentials",
            },
        },
        "manual_smoke_required": True,
        "note": (
            "Configuration presence only: this command does not validate credentials, "
            "contact providers, or prove live ingestion."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args()
    report = preflight()
    if args.format == "json":
        print(json.dumps(report, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
