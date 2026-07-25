"""Validate the frozen COR-123 demo contract without mutating shared state.

This command is intentionally preparation-only. It emits the exact safe inputs
that a trusted runtime ingester/reset executor consumes; it never writes SQL,
Qdrant, provider data, or credentials by itself.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any

from cortex.config import Settings
from cortex.demo.golden_incident import (
    expected_counts,
    load_golden_incident_manifest,
)
from cortex.embeddings.profile import EmbeddingIndexProfile

SCHEMA_VERSION = "cortex.demo_preparation.v1"


def preparation_report(*, phase: str, settings: Settings) -> dict[str, Any]:
    manifest = load_golden_incident_manifest()
    profile = EmbeddingIndexProfile.from_settings(settings)
    selected = (
        manifest.pre_live_records
        if phase == "pre_live"
        else (*manifest.pre_live_records, manifest.live_record)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "mutation_performed": False,
        "workspace_id": manifest.workspace_id,
        "task_ref": manifest.task_ref,
        "phase": phase,
        "manifest_sha256": manifest.sha256,
        "expected_corpus": asdict(expected_counts(manifest)),
        "selected_record_count": len(selected),
        "selected_fixture_ids": [record.fixture_id for record in selected],
        "embedding_profile": {
            "mode": profile.mode,
            "provider": profile.provider,
            "model": profile.model,
            "version": profile.version,
            "dimensions": profile.dimensions,
            "collection": profile.collection,
        },
        "reset_scope": {
            "workspace_id": manifest.workspace_id,
            "idempotency_prefix": "golden-incident:",
            "safe_to_apply_to_other_workspaces": False,
            "execution": "not_run",
        },
        "disclosure": (
            "Synthetic COR-123 preparation contract. This validation performs no "
            "database, vector-index, provider, or credential operation."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the frozen Cortex COR-123 demo preparation contract."
    )
    parser.add_argument(
        "--phase",
        choices=("pre_live", "post_live"),
        default="pre_live",
    )
    parser.add_argument(
        "--embedding-mode",
        choices=("deterministic", "real"),
        default="deterministic",
    )
    parser.add_argument("--format", choices=("json",), default="json")
    args = parser.parse_args(argv)
    report = preparation_report(
        phase=args.phase,
        settings=Settings(cortex_embedding_mode=args.embedding_mode),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
