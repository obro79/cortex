from cortex.dev.workbench import DevWorkbenchService


def test_evidence_pack_contains_claims_citations_conflicts_and_coverage() -> None:
    service = DevWorkbenchService()
    service.seed()
    service.query("COR-123")
    evidence = service.get_evidence_pack("ep-cor-123")
    assert evidence is not None

    assert evidence["claims"]
    assert len(evidence["citations"]) == 6
    assert evidence["source_coverage"] == {
        "slack": True,
        "diagram_ocr": True,
        "linear": True,
        "github": True,
        "repo_docs": True,
    }
    assert evidence["stale_evidence"] == ["repo-doc-session-storage"]
    assert evidence["conflicting_evidence"]
    assert evidence["permission_exclusions"] == []


def test_every_citation_resolves_to_seeded_source_object_or_file() -> None:
    service = DevWorkbenchService()
    service.seed()
    service.query("COR-123")
    evidence = service.get_evidence_pack("ep-cor-123")
    assert evidence is not None
    source_ids = service.repository.source_ids()

    for citation in evidence["citations"]:
        assert citation["source_object_id"] in source_ids
        if citation["source_file_id"] is not None:
            assert citation["source_file_id"] in source_ids
