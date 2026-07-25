"""Bounded normalization for synthetic, provider-labelled demo records."""

from __future__ import annotations

import json
from typing import Any

from cortex.contracts.entities import RawEvent
from cortex.normalization.normalizers.fixtures import (
    FixtureNormalizationError,
    normalize_fixture_payload,
)
from cortex.normalization.result import NormalizationResult

NORMALIZED_VERSION = "demo-snapshot-normalizer-v1"
DEMO_EVENT_SUFFIXES = (".demo_snapshot", ".demo_simulated")
DEMO_PROVIDERS = {
    "slack",
    "github",
    "jira",
    "email",
    "google_drive",
    "agent_session",
}


def normalize_demo_snapshot_payload(
    raw_event: RawEvent, payload_bytes: bytes
) -> NormalizationResult:
    """Normalize only the explicit synthetic demo envelope.

    Native provider event types continue through their provider normalizers.  This
    envelope intentionally retains the provider label while making its synthetic
    origin durable source metadata.
    """
    if not raw_event.event_type.endswith(DEMO_EVENT_SUFFIXES):
        raise FixtureNormalizationError("unsupported demo event type")
    if raw_event.provider not in DEMO_PROVIDERS:
        raise FixtureNormalizationError("unsupported demo provider")

    payload = _load_payload(payload_bytes)
    if payload.get("synthetic_demo") is not True:
        raise FixtureNormalizationError("demo payload must be explicitly synthetic")
    if payload.get("provider") != raw_event.provider:
        raise FixtureNormalizationError("demo payload provider must match raw event")
    if payload.get("mode") not in {"imported_snapshot", "simulated_fallback"}:
        raise FixtureNormalizationError("demo payload has an invalid mode")
    if not isinstance(payload.get("decisive"), bool):
        raise FixtureNormalizationError("demo payload decisive flag is required")
    if not isinstance(payload.get("manifest_sha256"), str):
        raise FixtureNormalizationError("demo payload manifest hash is required")

    result = normalize_fixture_payload(raw_event, payload_bytes)
    source_objects = [
        source_object.model_copy(
            update={
                "normalized_version": NORMALIZED_VERSION,
                "metadata_json": {
                    **source_object.metadata_json,
                    "synthetic_demo": True,
                    "demo_mode": payload["mode"],
                    "decisive": payload["decisive"],
                    "manifest_sha256": payload["manifest_sha256"],
                },
            }
        )
        for source_object in result.source_objects
    ]
    return result.model_copy(
        update={
            "normalized_version": NORMALIZED_VERSION,
            "source_objects": source_objects,
        }
    )


def _load_payload(payload_bytes: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError as error:
        raise FixtureNormalizationError("demo payload is not valid JSON") from error
    if not isinstance(payload, dict):
        raise FixtureNormalizationError("demo payload must be a JSON object")
    return payload
