"""Deterministic, explicitly synthetic COR-123 incident corpus."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
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

Provider = Literal[
    "slack", "github", "jira", "email", "google_drive", "agent_session"
]
EvidenceClass = Literal[
    "decisive",
    "near_miss",
    "stale_conflicting_historical",
    "operational_coordination",
    "unrelated",
]

PROVIDERS: tuple[Provider, ...] = (
    "slack",
    "github",
    "jira",
    "email",
    "google_drive",
    "agent_session",
)
EXPECTED_PROVIDER_COUNTS = {
    "slack": 33,
    "github": 32,
    "jira": 31,
    "email": 31,
    "google_drive": 31,
    "agent_session": 31,
}
EXPECTED_CLASS_COUNTS = {
    "decisive": 6,
    "near_miss": 30,
    "stale_conflicting_historical": 42,
    "operational_coordination": 63,
    "unrelated": 48,
}


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GoldenIncidentRecord(_FrozenModel):
    fixture_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    provider: Provider
    mode: Literal["live", "imported_snapshot"]
    phase: Literal["pre_live", "live_transition"]
    decisive: bool
    evidence_class: EvidenceClass
    synthetic: Literal[True] = True
    source_type: str = Field(min_length=1, max_length=80)
    source_updated_at: datetime
    title: str = Field(min_length=1, max_length=300)
    citation_label: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=4_000)
    is_stale: bool = False

    @model_validator(mode="after")
    def validate_record(self) -> GoldenIncidentRecord:
        if self.phase == "live_transition" and self.mode != "live":
            raise ValueError("live_transition records must use live mode")
        if self.phase == "pre_live" and self.mode != "imported_snapshot":
            raise ValueError("pre_live records must use imported_snapshot mode")
        if self.decisive != (self.evidence_class == "decisive"):
            raise ValueError("decisive must match evidence_class")
        if self.evidence_class == "stale_conflicting_historical" and not self.is_stale:
            raise ValueError("historical conflicts must be marked stale")
        return self


class GoldenIncidentManifest(_FrozenModel):
    schema_version: Literal["cortex.golden_incident.v1"]
    workspace_id: Literal["ws_demo_cor_123"]
    task_ref: Literal["COR-123"]
    demo_epoch: datetime
    records: tuple[GoldenIncidentRecord, ...] = Field(min_length=189, max_length=189)

    @field_validator("records")
    @classmethod
    def validate_corpus(
        cls, records: tuple[GoldenIncidentRecord, ...]
    ) -> tuple[GoldenIncidentRecord, ...]:
        if len({record.fixture_id for record in records}) != len(records):
            raise ValueError("fixture IDs must be unique")
        provider_counts = Counter(record.provider for record in records)
        if dict(provider_counts) != EXPECTED_PROVIDER_COUNTS:
            raise ValueError("corpus provider counts do not match the golden contract")
        class_counts = Counter(record.evidence_class for record in records)
        if dict(class_counts) != EXPECTED_CLASS_COUNTS:
            raise ValueError(
                "corpus evidence-class counts do not match the golden contract"
            )
        if sum(record.decisive for record in records) != 6:
            raise ValueError("corpus must contain exactly six decisive records")
        decisive_provider_counts = Counter(
            record.provider for record in records if record.decisive
        )
        if dict(decisive_provider_counts) != {provider: 1 for provider in PROVIDERS}:
            raise ValueError("corpus requires exactly one decisive record per provider")
        if sum(record.phase == "pre_live" for record in records) != 188:
            raise ValueError("corpus must contain exactly 188 pre-live snapshots")
        live = [record for record in records if record.phase == "live_transition"]
        if len(live) != 1 or live[0].provider != "slack" or not live[0].decisive:
            raise ValueError("corpus requires one decisive live Slack transition")
        if not all(record.synthetic for record in records):
            raise ValueError("golden incident records must be explicitly synthetic")
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
            "evidence_class": record.evidence_class,
            "source_type": record.source_type,
            "source_updated_at": record.source_updated_at.isoformat(),
            "title": record.title,
            "citation_label": record.citation_label,
            "content": record.content,
            "is_stale": record.is_stale,
            "synthetic_demo": True,
            "synthetic": record.synthetic,
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
    near_miss: int
    stale_conflicting_historical: int
    operational_coordination: int
    unrelated: int


def _source_type(provider: Provider) -> str:
    return {
        "slack": "message",
        "github": "issue",
        "jira": "issue",
        "email": "message",
        "google_drive": "document",
        "agent_session": "checkpoint",
    }[provider]


def _generated_record(
    provider: Provider, evidence_class: EvidenceClass, ordinal: int, epoch: datetime
) -> GoldenIncidentRecord:
    label = provider.replace("_", " ").title()
    topic = {
        "near_miss": (
            "a superficially similar cache symptom that does not affect session reads"
        ),
        "stale_conflicting_historical": (
            "superseded historical guidance that conflicts with the current "
            "Postgres rollout"
        ),
        "operational_coordination": (
            "incident coordination, ownership, or verification planning"
        ),
        "unrelated": "an unrelated maintenance or product-work item",
    }[evidence_class]
    updated_at = epoch - timedelta(minutes=10 + ordinal)
    if evidence_class == "stale_conflicting_historical":
        updated_at = epoch - timedelta(days=30 + ordinal)
    return GoldenIncidentRecord(
        fixture_id=(
            f"{provider.replace('_', '-')}-"
            f"{evidence_class.replace('_', '-')}-{ordinal:02d}"
        ),
        provider=provider,
        mode="imported_snapshot",
        phase="pre_live",
        decisive=False,
        evidence_class=evidence_class,
        synthetic=True,
        source_type=_source_type(provider),
        source_updated_at=updated_at,
        title=f"Synthetic {label} {evidence_class.replace('_', ' ')} {ordinal:02d}",
        citation_label=f"Synthetic {label} fixture {ordinal:02d}",
        content=(
            f"Synthetic COR-123 fixture {ordinal:02d} from {label}: {topic}. "
            "It is deterministic test data and does not represent live provider data."
        ),
        is_stale=evidence_class == "stale_conflicting_historical",
    )


def _generate_records(
    seed_records: tuple[GoldenIncidentRecord, ...], demo_epoch: datetime
) -> tuple[GoldenIncidentRecord, ...]:
    """Expand six inspectable decisive anchors into the fixed 189-record corpus."""
    generated: list[GoldenIncidentRecord] = list(seed_records)
    allocations: dict[EvidenceClass, dict[Provider, int]] = {
        "stale_conflicting_historical": {provider: 7 for provider in PROVIDERS},
        "operational_coordination": {
            "slack": 12,
            "github": 11,
            "jira": 10,
            "email": 10,
            "google_drive": 10,
            "agent_session": 10,
        },
        "unrelated": {provider: 8 for provider in PROVIDERS},
        "near_miss": {provider: 5 for provider in PROVIDERS},
    }
    for evidence_class, provider_allocations in allocations.items():
        for provider in PROVIDERS:
            generated.extend(
                _generated_record(provider, evidence_class, ordinal, demo_epoch)
                for ordinal in range(1, provider_allocations[provider] + 1)
            )
    return tuple(generated)


def load_golden_incident_manifest(
    path: Path = DEFAULT_MANIFEST_PATH,
) -> GoldenIncidentManifest:
    """Load six inspectable anchors and deterministically expand the corpus."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    seed_records = tuple(
        GoldenIncidentRecord.model_validate(item) for item in payload.pop("records")
    )
    payload.pop("generator", None)
    if len(seed_records) != 6:
        raise ValueError(
            "golden incident fixture must define exactly six decisive anchors"
        )
    demo_epoch = datetime.fromisoformat(payload["demo_epoch"].replace("Z", "+00:00"))
    return GoldenIncidentManifest.model_validate(
        {**payload, "records": _generate_records(seed_records, demo_epoch)}
    )


def expected_counts(manifest: GoldenIncidentManifest) -> GoldenIncidentExpectedCounts:
    classes = Counter(record.evidence_class for record in manifest.records)
    return GoldenIncidentExpectedCounts(
        records=len(manifest.records),
        decisive=sum(record.decisive for record in manifest.records),
        distractors=sum(not record.decisive for record in manifest.records),
        pre_live=len(manifest.pre_live_records),
        live_transition=1,
        providers=len({record.provider for record in manifest.records}),
        near_miss=classes["near_miss"],
        stale_conflicting_historical=classes["stale_conflicting_historical"],
        operational_coordination=classes["operational_coordination"],
        unrelated=classes["unrelated"],
    )
