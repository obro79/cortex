from __future__ import annotations

import json

from cortex.demo import DemoEvidenceControlPlane


async def test_report_has_deterministic_fixture_counts_and_blocked_handoff() -> None:
    report = await DemoEvidenceControlPlane().build_report()

    assert report.scope == "COR-123"
    assert report.live_data is False
    assert report.corpus.source_object_count == 10
    assert report.corpus.source_file_count == 3
    assert report.corpus.provider_counts == {
        "github": 1,
        "google_drive": 2,
        "jira": 1,
        "linear": 2,
        "repo_docs": 1,
        "slack": 3,
    }
    assert report.corpus.media_counts == {"caption": 2, "video_transcript": 1}
    assert report.pipeline.status == "completed"
    assert report.pipeline.stage_count == 10
    assert report.pipeline.stage_status_counts == {"completed": 10}
    assert report.decision.gate_status == "block"
    assert report.decision.handoff_status == "blocked_pending_human_review"


async def test_report_is_json_ready_and_excludes_fixture_content_and_urls() -> None:
    report = await DemoEvidenceControlPlane().build_report()

    serialized = json.dumps(report.as_dict(), sort_keys=True)
    assert "https://" not in serialized
    assert "Postgres is the approved" not in serialized
    assert "fixture://" not in serialized
    assert report.as_dict()["incremental_ingest_timeline"] == [
        {"offset_seconds": 0, "stage": "seed", "status": "completed"},
        {"offset_seconds": 1, "stage": "ingest", "status": "completed"},
        {"offset_seconds": 2, "stage": "kafka_event", "status": "completed"},
        {"offset_seconds": 3, "stage": "normalize", "status": "completed"},
        {"offset_seconds": 4, "stage": "chunk_ocr", "status": "completed"},
        {"offset_seconds": 5, "stage": "embed", "status": "completed"},
        {"offset_seconds": 6, "stage": "index", "status": "completed"},
        {"offset_seconds": 7, "stage": "link", "status": "completed"},
        {"offset_seconds": 8, "stage": "retrieve", "status": "completed"},
        {"offset_seconds": 9, "stage": "gate", "status": "completed"},
    ]
