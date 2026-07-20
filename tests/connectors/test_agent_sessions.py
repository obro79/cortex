from __future__ import annotations

import pytest

from cortex.connectors.agent_sessions import (
    EXPORT_MARKER,
    AgentCheckpointDeletionPlan,
    AgentCheckpointExport,
    AgentCheckpointImportPlan,
    AgentCheckpointProvider,
    AgentCheckpointVisibility,
    content_hash_for_checkpoint,
)
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository
from cortex.ingestion.service import RawEventIngestionService


def checkpoint_content(**updates: object) -> dict[str, object]:
    content: dict[str, object] = {
        "checkpoint_id": "checkpoint_1",
        "provider": "codex",
        "task_state": "in_progress",
        "task_summary": "Implement the checkpoint source boundary.",
        "decisions": [{"summary": "Use explicit exports only.", "rationale": None}],
        "files": [
            {
                "path": "src/cortex/connectors/agent_sessions/service.py",
                "summary": "Adds the shared-ingestion adapter.",
                "sensitive_path": False,
            }
        ],
        "commands": [],
        "tests": [],
        "next_actions": ["Run focused tests."],
        "evidence_references": [],
        "visibility": "private",
    }
    content.update(updates)
    return content


def make_export(**updates: object) -> AgentCheckpointExport:
    content = checkpoint_content(**updates)
    return AgentCheckpointExport(
        export_marker=EXPORT_MARKER,
        export_enabled=True,
        local_session_ref="caller-export-reference-0001",
        content_hash=content_hash_for_checkpoint(content),
        **content,
    )


async def test_explicit_checkpoint_export_uses_common_raw_event_ingestion() -> None:
    plan = AgentCheckpointImportPlan(
        workspace_id="ws_1",
        source_connection_id="src_agent_checkpoint",
        checkpoint=make_export(),
    )
    repository = InMemoryRawEventRepository()
    event_bus = InMemoryEventBus()
    ingestion = RawEventIngestionService(
        repository, InMemoryPayloadStore(), RawEventPublisher(event_bus)
    )

    execution = await plan.execute(ingestion)

    raw_event = repository.get_by_id(execution.result.raw_event_id)
    assert raw_event.provider == "agent_session"
    assert raw_event.event_type == "agent_session.checkpoint.exported"
    assert raw_event.external_object_key == "agent_session:checkpoint:checkpoint_1"
    assert event_bus.list_events()[0].payload == {
        "provider_event_type": "agent_session.checkpoint.exported"
    }


def test_checkpoint_contract_defaults_to_private_visibility_and_hashes_local_ref() -> (
    None
):
    export = make_export()

    payload = export.to_payload()

    assert export.visibility == AgentCheckpointVisibility.PRIVATE
    assert payload["local_session_ref_hash"].startswith("sha256:")
    assert "caller-export-reference" not in str(payload)
    assert "native_session_id" not in payload
    assert "control_handle" not in payload


def test_checkpoint_contract_rejects_transcripts_native_handles_and_secrets() -> None:
    content = checkpoint_content()
    with pytest.raises(ValueError):
        AgentCheckpointExport(
            export_marker=EXPORT_MARKER,
            export_enabled=True,
            local_session_ref="caller-export-reference-0001",
            content_hash=content_hash_for_checkpoint(content),
            **content,
            native_session_id="private-native-id",
        )

    secret_content = checkpoint_content(
        task_summary="Use sk_12345678901234567890123456789012"
    )
    with pytest.raises(ValueError, match="redact"):
        AgentCheckpointExport(
            export_marker=EXPORT_MARKER,
            export_enabled=True,
            local_session_ref="caller-export-reference-0001",
            content_hash=content_hash_for_checkpoint(secret_content),
            **secret_content,
        )


def test_checkpoint_contract_fails_closed_for_export_marker_visibility_and_hash() -> (
    None
):
    content = checkpoint_content(visibility="workspace")
    with pytest.raises(ValueError):
        AgentCheckpointExport(
            export_marker=EXPORT_MARKER,
            export_enabled=True,
            local_session_ref="caller-export-reference-0001",
            content_hash="sha256:" + "0" * 64,
            **content,
        )
    with pytest.raises(ValueError):
        AgentCheckpointExport(
            export_marker="not_an_export",  # type: ignore[arg-type]
            export_enabled=True,
            local_session_ref="caller-export-reference-0001",
            content_hash=content_hash_for_checkpoint(content),
            **content,
        )
    with pytest.raises(ValueError):
        AgentCheckpointExport(
            export_marker=EXPORT_MARKER,
            export_enabled=False,  # type: ignore[arg-type]
            local_session_ref="caller-export-reference-0001",
            content_hash=content_hash_for_checkpoint(content),
            **content,
        )


def test_deletion_revocation_plan_is_local_lifecycle_seam_not_agent_control() -> None:
    plan = AgentCheckpointDeletionPlan(
        checkpoint_id="checkpoint_1",
        local_session_ref_hash="sha256:" + "a" * 64,
        action="revoke_export",
    )

    assert plan.external_object_key == "agent_session:checkpoint:checkpoint_1"


def test_contract_is_provider_neutral() -> None:
    content = checkpoint_content(provider="cursor")
    export = AgentCheckpointExport(
        export_marker=EXPORT_MARKER,
        export_enabled=True,
        local_session_ref="caller-export-reference-0001",
        content_hash=content_hash_for_checkpoint(content),
        **content,
    )

    assert export.provider == AgentCheckpointProvider.CURSOR
