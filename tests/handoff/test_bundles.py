from cortex.handoff import create_handoff_bundle


def test_create_handoff_bundle_is_portable_and_never_accesses_a_session() -> None:
    response = create_handoff_bundle(
        {
            "approved_summary": "Use the approved Postgres migration path.",
            "evidence_references": [
                "evidence-pack:ep_123",
                {"url": "https://example.test/decision/123", "label": "Decision"},
            ],
        }
    )

    assert response["ok"] is True
    bundle = response["bundle"]
    assert bundle["approved_summary"] == "Use the approved Postgres migration path."
    assert bundle["evidence_references"][0] == "evidence-pack:ep_123"
    assert bundle["session_accessed"] is False
    assert bundle["retrieval_runtime"]["configured"] is False
    assert bundle["native_claude_resume_supported"] is False
    assert bundle["native_claude_fork_supported"] is False
    assert bundle["native_claude"]["resume"]["supported"] is False
    assert bundle["native_claude"]["fork"]["supported"] is False


def test_create_handoff_bundle_rejects_invalid_summary_and_references() -> None:
    missing_summary = create_handoff_bundle({"evidence_references": []})
    invalid_references = create_handoff_bundle(
        {"approved_summary": "Approved", "evidence_references": "ep_123"}
    )

    assert missing_summary["error"] == "invalid_arguments"
    assert missing_summary["fields"] == ["approved_summary"]
    assert invalid_references["error"] == "invalid_arguments"
    assert invalid_references["fields"] == ["evidence_references"]


def test_create_handoff_bundle_requires_opt_in_for_opaque_handles() -> None:
    rejected = create_handoff_bundle(
        {"approved_summary": "Approved", "opaque_handles": ["opaque:abc"]}
    )
    accepted = create_handoff_bundle(
        {
            "approved_summary": "Approved",
            "opaque_handles": ["opaque:abc"],
            "handoff_opt_in": True,
        }
    )

    assert rejected["error"] == "handoff_opt_in_required"
    assert accepted["ok"] is True
    assert accepted["bundle"]["opaque_handles"] == ["opaque:abc"]
    assert accepted["bundle"]["handoff_opt_in"] is True
