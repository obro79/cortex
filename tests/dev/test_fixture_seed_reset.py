from cortex.dev.workbench import DevWorkbenchService


def test_seed_uses_stable_ids_and_is_idempotent() -> None:
    service = DevWorkbenchService()
    first = service.seed()
    second = service.seed()

    assert first["fixture_ids"] == second["fixture_ids"]
    assert "slack-thread-sessions-postgres" in first["fixture_ids"]
    assert "linear-issue-COR-123" in first["fixture_ids"]
    assert first["counts"] == second["counts"]
    assert first["counts"]["raw_events"] == 10
    assert first["counts"]["source_objects"] == 10
    assert first["counts"]["source_files"] == 3
    assert first["provider_counts"] == {
        "github": 1,
        "google_drive": 2,
        "jira": 1,
        "linear": 2,
        "repo_docs": 1,
        "slack": 3,
    }
    assert first["media_counts"] == {"caption": 2, "video_transcript": 1}


def test_fixture_media_is_explicitly_deterministic_and_not_live() -> None:
    service = DevWorkbenchService()
    service.seed()

    assert len(service.repository.source_files) == 3
    for source_file in service.repository.source_files.values():
        provenance = source_file.metadata_json["provenance"]
        assert source_file.metadata_json["fixture"] is True
        assert source_file.metadata_json["deterministic"] is True
        assert "not live OCR or transcription" in provenance


def test_reset_clears_dev_state_only() -> None:
    service = DevWorkbenchService()
    service.seed()
    reset = service.reset()

    assert reset["status"] == "reset"
    assert reset["state"]["seeded"] is False
    assert reset["state"]["fixture_counts"]["source_objects"] == 0
