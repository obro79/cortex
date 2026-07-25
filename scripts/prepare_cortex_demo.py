"""Validate or rehearse the deterministic COR-123 demo corpus.

``validate`` is always non-mutating.  ``seed`` and ``reset`` require the
explicit ``--in-memory`` switch and only affect a disposable in-memory runtime;
they cannot target SQL, Qdrant, provider data, or credentials.
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
from cortex.demo.seed import InMemoryDemoRuntime, inputs_for_phase, reset_scope
from cortex.embeddings.profile import EmbeddingIndexProfile

SCHEMA_VERSION = "cortex.demo_preparation.v1"


def preparation_report(*, phase: str, settings: Settings) -> dict[str, Any]:
    manifest = load_golden_incident_manifest()
    profile = EmbeddingIndexProfile.from_settings(settings)
    selected = inputs_for_phase(manifest, phase)  # type: ignore[arg-type]
    scope = reset_scope(manifest)
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
        "selected_fixture_ids": [
            str(item.payload["fixture_id"]) for item in selected
        ],
        "embedding_profile": {
            "mode": profile.mode,
            "provider": profile.provider,
            "model": profile.model,
            "version": profile.version,
            "dimensions": profile.dimensions,
            "collection": profile.collection,
        },
        "reset_scope": {
            "workspace_id": scope.workspace_id,
            "idempotency_prefix": "golden-incident:",
            "raw_event_count": len(scope.raw_event_ids),
            "external_object_key_count": len(scope.external_object_keys),
            "safe_to_apply_to_other_workspaces": False,
            "execution": "not_run",
        },
        "disclosure": (
            "Synthetic COR-123 preparation contract. This validation performs no "
            "database, vector-index, provider, or credential operation."
        ),
    }


async def in_memory_mutation_report(*, command: str, phase: str) -> dict[str, Any]:
    """Run only the disposable rehearsal runtime used by tests and local demos."""
    manifest = load_golden_incident_manifest()
    runtime = InMemoryDemoRuntime(manifest)
    if command == "seed":
        result = await runtime.seed(phase=phase)  # type: ignore[arg-type]
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "command": command,
            "mutation_performed": True,
            "mutation_target": "in_memory_demo_runtime",
            "workspace_id": manifest.workspace_id,
            "phase": result.phase,
            "selected_record_count": result.selected_record_count,
            "created_count": result.created_count,
            "existing_count": result.existing_count,
            "published_count": result.published_count,
            "raw_event_count": len(runtime.repository.list_all(manifest.workspace_id)),
            "normalization": (
                "published to raw_event.persisted; worker dispatch is external"
            ),
        }
    if command == "reset":
        scope = await runtime.reset()
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "command": command,
            "mutation_performed": True,
            "mutation_target": "in_memory_demo_runtime",
            "workspace_id": scope.workspace_id,
            "raw_event_count": len(scope.raw_event_ids),
            "safe_to_apply_to_other_workspaces": False,
            "reset_execution": "runtime_replaced",
        }
    raise ValueError(f"unsupported mutation command: {command}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the frozen Cortex COR-123 demo preparation contract."
    )
    parser.add_argument(
        "--command",
        choices=("validate", "seed", "reset"),
        default="validate",
        help="validate is read-only; seed/reset require --in-memory",
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
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help="allow a mutation only in the disposable in-memory runtime",
    )
    args = parser.parse_args(argv)
    if args.command == "validate":
        report = preparation_report(
            phase=args.phase,
            settings=Settings(cortex_embedding_mode=args.embedding_mode),
        )
    else:
        if not args.in_memory:
            parser.error(
                "seed/reset require --in-memory; durable mutation is not implicit"
            )
        import asyncio

        report = asyncio.run(
            in_memory_mutation_report(command=args.command, phase=args.phase)
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
