"""Validate Live Context Proof prerequisites without using secrets or a network.

This is an operator gate, not a health check and not evidence of ingestion.  It
reports environment-variable *presence* and local Compose state only.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlparse

REPORT_SCHEMA_VERSION: Final = "live-context-preflight/v1"
LIVE_REPORT_SCHEMA_VERSION: Final = "live-context-run-report/v1"
ROOT = Path(__file__).resolve().parents[1]

_REQUIRED_PRESENCE: Final = (
    "DATABASE_URL",
    "KAFKA_BOOTSTRAP_SERVERS",
    "QDRANT_URL",
    "GEMINI_API_KEY",
    "CORTEX_SECRET_ENCRYPTION_KEY",
    "SLACK_CLIENT_ID",
    "SLACK_CLIENT_SECRET",
    "SLACK_SIGNING_SECRET",
    "SLACK_REDIRECT_URI",
)
_RUNTIME_CONTRACT: Final = {
    "CORTEX_EVENT_BUS": "kafka",
    "CORTEX_STATE_BACKEND": "sql",
    "CORTEX_EMBEDDING_MODE": "real",
    "CORTEX_SLACK_CONNECTOR_ENABLED": "true",
}
_COUNT_FIELDS: Final = (
    "raw_events",
    "source_objects",
    "source_chunks",
    "embeddings_completed",
    "vector_points_verified",
    "query_requests",
    "evidence_packs",
    "failures",
)


def _present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _presence(names: tuple[str, ...]) -> dict[str, bool]:
    return {name: _present(name) for name in names}


def _local_qdrant(url: str) -> bool:
    return urlparse(url).hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
        "qdrant",
        "host.docker.internal",
    }


def _qdrant_contract() -> dict[str, Any]:
    url = os.getenv("QDRANT_URL", "").strip()
    prefix = os.getenv("QDRANT_COLLECTION_PREFIX", "cortex").strip()
    parsed = urlparse(url)
    hosted = bool(url) and not _local_qdrant(url)
    url_valid = (
        bool(url) and parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    )
    api_key_required = hosted
    api_key_present = _present("QDRANT_API_KEY")
    return {
        "url_present": bool(url),
        "url_valid": url_valid,
        "hosted": hosted,
        "api_key_required": api_key_required,
        "api_key_present": api_key_present,
        "transport_valid": not hosted or parsed.scheme == "https",
        "collection_prefix_present": bool(prefix),
        "collection_name_resolved": False,
        "note": (
            "Collection identity is resolved by the runtime embedding profile; "
            "no collection is contacted."
        ),
    }


def _runtime_contract() -> dict[str, dict[str, object]]:
    return {
        name: {"expected": expected, "matches": os.getenv(name, "").lower() == expected}
        for name, expected in _RUNTIME_CONTRACT.items()
    }


def _migration_contract() -> dict[str, object]:
    versions = ROOT / "alembic" / "versions"
    revision_files = sorted(versions.glob("*.py")) if versions.is_dir() else []
    return {
        "alembic_ini_present": (ROOT / "alembic.ini").is_file(),
        "versions_directory_present": versions.is_dir(),
        "revision_file_count": len(revision_files),
        "migration_execution": "not_run",
        "note": (
            "Run the explicit migrate service before a controlled live run; "
            "this preflight never changes schema."
        ),
    }


def _compose_readiness() -> dict[str, object]:
    """Check local Compose metadata when Docker is installed; never starts it."""
    if shutil.which("docker") is None:
        return {"available": False, "checked": False, "status": "docker_unavailable"}
    try:
        result = subprocess.run(
            ("docker", "compose", "config", "--quiet"),
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"available": True, "checked": False, "status": "compose_unavailable"}
    return {
        "available": True,
        "checked": True,
        "status": "configured" if result.returncode == 0 else "compose_config_failed",
    }


def _next_action(*, configuration_ready: bool, compose: dict[str, object]) -> str:
    if not configuration_ready:
        return (
            "Configure the missing presence-only prerequisites, then rerun this "
            "command."
        )
    if compose["status"] != "configured":
        return (
            "Run `docker compose config --quiet`, resolve local Compose readiness, "
            "then run migrations."
        )
    return (
        "Run migrations, start local dependencies, complete Slack OAuth, then "
        "record a redacted live-context run report."
    )


def preflight() -> dict[str, object]:
    """Build the stable, redacted preflight report without provider requests."""
    environment = _presence(_REQUIRED_PRESENCE)
    runtime = _runtime_contract()
    qdrant = _qdrant_contract()
    migration = _migration_contract()
    compose = _compose_readiness()
    configuration_ready = (
        all(environment.values())
        and all(bool(item["matches"]) for item in runtime.values())
        and bool(qdrant["url_valid"])
        and bool(qdrant["collection_prefix_present"])
        and (not bool(qdrant["api_key_required"]) or bool(qdrant["api_key_present"]))
        and bool(qdrant["transport_valid"])
        and bool(migration["alembic_ini_present"])
        and bool(migration["versions_directory_present"])
    )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": "preflight",
        "ok": configuration_ready and compose["status"] == "configured",
        "network_access": False,
        "provider_calls": False,
        "secret_values_emitted": False,
        "configuration_ready": configuration_ready,
        "environment": environment,
        "runtime_contract": runtime,
        "qdrant_contract": qdrant,
        "migration_contract": migration,
        "local_dependencies": compose,
        "next_action": _next_action(
            configuration_ready=configuration_ready, compose=compose
        ),
        "disclosure": (
            "Presence-only preflight. This does not validate credentials, run "
            "migrations, contact Qdrant, contact Slack, or prove ingestion."
        ),
    }


def validate_live_run_report(report: object) -> list[str]:
    """Validate the intentionally redacted report contract saved after a live run."""
    if not isinstance(report, dict):
        return ["report must be a JSON object"]
    allowed = {
        "schema_version",
        "mode",
        "outcome",
        "live_data",
        "run_id_hash",
        "environment",
        "provider",
        "source_ref_hash",
        "collection",
        "counts",
        "freshness_seconds",
        "stages",
        "disclosure",
        "next_action",
    }
    errors = [f"unexpected field: {key}" for key in report if key not in allowed]
    required = allowed - {"freshness_seconds", "next_action"}
    errors.extend(f"missing field: {key}" for key in sorted(required - set(report)))
    if report.get("schema_version") != LIVE_REPORT_SCHEMA_VERSION:
        errors.append("schema_version must be live-context-run-report/v1")
    if report.get("mode") != "controlled_live_run":
        errors.append("mode must be controlled_live_run")
    if report.get("outcome") not in {"passed", "failed", "partial"}:
        errors.append("outcome must be passed, failed, or partial")
    if report.get("live_data") is not True:
        errors.append("live_data must be true")
    if report.get("provider") != "slack":
        errors.append("provider must be slack for this proof slice")
    for field in (
        "run_id_hash",
        "source_ref_hash",
        "collection",
        "environment",
        "disclosure",
    ):
        if not isinstance(report.get(field), str) or not report.get(field):
            errors.append(f"{field} must be a non-empty string")
    counts = report.get("counts")
    if not isinstance(counts, dict):
        errors.append("counts must be an object")
    else:
        errors.extend(
            f"counts missing: {field}" for field in _COUNT_FIELDS if field not in counts
        )
        errors.extend(
            f"counts.{field} must be a non-negative integer"
            for field in _COUNT_FIELDS
            if not isinstance(counts.get(field), int)
            or isinstance(counts.get(field), bool)
            or counts.get(field, -1) < 0
        )
        errors.extend(
            f"unexpected counts field: {field}"
            for field in counts
            if field not in _COUNT_FIELDS
        )
    if not isinstance(report.get("stages"), dict) or not report["stages"]:
        errors.append("stages must be a non-empty object of status codes")
    if "freshness_seconds" in report and (
        not isinstance(report["freshness_seconds"], int)
        or report["freshness_seconds"] < 0
    ):
        errors.append("freshness_seconds must be a non-negative integer")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--validate-report", type=Path, metavar="PATH")
    args = parser.parse_args()
    if args.validate_report:
        try:
            report = json.loads(args.validate_report.read_text())
        except (OSError, json.JSONDecodeError) as error:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "errors": [f"invalid JSON report: {error.__class__.__name__}"],
                    },
                    sort_keys=True,
                )
            )
            return 2
        errors = validate_live_run_report(report)
        print(json.dumps({"ok": not errors, "errors": errors}, sort_keys=True))
        return 0 if not errors else 1
    report = preflight()
    print(
        json.dumps(report, sort_keys=True)
        if args.format == "json"
        else json.dumps(report, indent=2, sort_keys=True)
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
