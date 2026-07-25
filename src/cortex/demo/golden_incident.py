"""Frozen, synthetic COR-123 manifest and shared-ingestion inputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cortex.ingestion.payloads import canonical_json_bytes
from cortex.ingestion.raw_events import RawEventInput

DEFAULT_MANIFEST_PATH = (
    Path(__file__).resolve().parents[3]
    / "fixtures"
    / "golden_incident"
    / "manifest.json"
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GoldenIncidentRecord(_FrozenModel):
    fixture_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    provider: Literal[
        "slack", "github", "jira", "email", "google_drive", "agent_session"
    ]
    mode: Literal["live", "imported_snapshot"]
    phase: Literal["pre_live", "live_transition"]
    decisive: bool
    source_type: str = Field(min_length=1, max_length=80)
    source_updated_at: datetime
    title: str = Field(min_length=1, max_length=300)
    citation_label: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=4_000)
    is_stale: bool = False

    @model_validator(mode="after")
    def phase_matches_mode(self) -> GoldenIncidentRecord:
        if self.phase == "live_transition" and self.mode != "live":
            raise ValueError("live_transition records must use live mode")
        if self.phase == "pre_live" and self.mode != "imported_snapshot":
            raise ValueError("pre_live records must use imported_snapshot mode")
        return self


class GoldenIncidentManifest(_FrozenModel):
    schema_version: Literal["cortex.golden_incident.v1"]
    workspace_id: Literal["ws_demo_cor_123"]
    task_ref: Literal["COR-123"]
    demo_epoch: datetime
    records: tuple[GoldenIncidentRecord, ...] = Field(min_length=18, max_length=18)

    @field_validator("records")
    @classmethod
    def validate_corpus(
        cls, records: tuple[GoldenIncidentRecord, ...]
    ) -> tuple[GoldenIncidentRecord, ...]:
        if len({record.fixture_id for record in records}) != len(records):
            raise ValueError("fixture IDs must be unique")
        if sum(record.decisive for record in records) != 6:
            raise ValueError("corpus must contain exactly six decisive records")
        if sum(not record.decisive for record in records) != 12:
            raise ValueError("corpus must contain exactly twelve distractors")
        if sum(record.phase == "pre_live" for record in records) != 17:
            raise ValueError("corpus must contain exactly seventeen pre-live records")
        live = [record for record in records if record.phase == "live_transition"]
        if len(live) != 1 or live[0].provider != "slack" or not live[0].decisive:
            raise ValueError("corpus requires one decisive live Slack transition")
        required = {
            "slack",
            "github",
            "jira",
            "email",
            "google_drive",
            "agent_session",
        }
        if {record.provider for record in records} != required:
            raise ValueError("corpus provider coverage is incomplete")
        return records

    @property
    def sha256(self) -> str:
        payload = self.model_dump(mode="json")
        return f"sha256:{sha256(canonical_json_bytes(payload)).hexdigest()}"

    @property
    def pre_live_records(self) -> tuple[GoldenIncidentRecord, ...]:
        return tuple(record for record in self.records if record.phase == "pre_live")

    @property
    def live_record(self) -> GoldenIncidentRecord:
        return next(
            record for record in self.records if record.phase == "live_transition"
        )

    def raw_event_input(self, record: GoldenIncidentRecord) -> RawEventInput:
        payload: dict[str, Any] = {
            "fixture_id": record.fixture_id,
            "provider": record.provider,
            "object_type": f"demo_{record.source_type}",
            "source_kind": f"demo_{record.source_type}",
            "task_ref": self.task_ref,
            "mode": (
                "simulated_fallback"
                if record.phase == "live_transition"
                else record.mode
            ),
            "decisive": record.decisive,
            "source_type": record.source_type,
            "source_updated_at": record.source_updated_at.isoformat(),
            "title": record.title,
            "citation_label": record.citation_label,
            "content": record.content,
            "is_stale": record.is_stale,
            "synthetic_demo": True,
            "manifest_sha256": self.sha256,
        }
        return RawEventInput(
            workspace_id=self.workspace_id,
            source_connection_id=f"src_demo_{record.provider}",
            provider=record.provider,
            external_event_id=f"golden:{record.fixture_id}",
            event_type=(
                f"{record.provider}.{record.source_type}."
                f"{'demo_simulated' if record.mode == 'live' else 'demo_snapshot'}"
            ),
            external_object_key=f"{record.provider}:{record.fixture_id}",
            idempotency_key=f"golden-incident:{record.fixture_id}",
            payload=payload,
            occurred_at=record.source_updated_at,
            trace_id="golden-incident-prepare",
            raw_event_id=f"raw_golden_{record.fixture_id.replace('-', '_')}",
        )

    def pre_live_inputs(self) -> tuple[RawEventInput, ...]:
        return tuple(self.raw_event_input(record) for record in self.pre_live_records)

    def live_input(self) -> RawEventInput:
        return self.raw_event_input(self.live_record)


@dataclass(frozen=True)
class GoldenIncidentExpectedCounts:
    records: int
    decisive: int
    distractors: int
    pre_live: int
    live_transition: int
    providers: int


def load_golden_incident_manifest(
    path: Path = DEFAULT_MANIFEST_PATH,
) -> GoldenIncidentManifest:
    return GoldenIncidentManifest.model_validate(
        json.loads(path.read_text(encoding="utf-8"))
    )


def expected_counts(
    manifest: GoldenIncidentManifest,
) -> GoldenIncidentExpectedCounts:
    return GoldenIncidentExpectedCounts(
        records=len(manifest.records),
        decisive=sum(record.decisive for record in manifest.records),
        distractors=sum(not record.decisive for record in manifest.records),
        pre_live=len(manifest.pre_live_records),
        live_transition=1,
        providers=len({record.provider for record in manifest.records}),
    )
