from pathlib import Path

PHASE = Path("docs/phases/phase-22-enterprise-readiness")
FOLLOWUP_PLAN = Path("docs/non-ui-enterprise-readiness-followup-autoplan.md")


def test_launch_checklist_declares_beta_status_and_blockers() -> None:
    text = (PHASE / "launch-checklist.md").read_text(encoding="utf-8")

    assert "invite-only beta" in text
    assert "Launch Blockers" in text
    assert "Complete Phase 15 onboarding routes" in text
    assert "Validate Stripe checkout" in text
    assert "Run staging restore, rollback, load, and cost drills" in text


def test_known_limitations_do_not_overclaim_enterprise_readiness() -> None:
    text = (PHASE / "known-limitations.md").read_text(encoding="utf-8")

    assert "not yet ready for unattended enterprise self-serve rollout" in text
    assert "full provider ACL parity is" in text
    assert "not claimed" in text
    assert "Production API/worker queueing and drill" in text


def test_sales_handoff_excludes_sensitive_support_intake() -> None:
    text = (PHASE / "sales-support-handoff.md").read_text(encoding="utf-8")

    assert "Do Not Promise" in text
    assert "Never request provider tokens" in text
    assert "raw private messages" in text
    assert "Trace ID" in text


def test_pricing_decision_stays_invite_only_until_billing_is_complete() -> None:
    text = (PHASE / "pricing-packaging-decision.md").read_text(encoding="utf-8")

    assert "invite-only beta packaging" in text
    assert "Stripe production activation is not complete" in text
    assert "Read access remains available" in text


def test_followup_autoplan_tracks_deep_review_blockers() -> None:
    text = FOLLOWUP_PLAN.read_text(encoding="utf-8")
    phase_readme = (PHASE / "README.md").read_text(encoding="utf-8")

    assert "Lifecycle correctness" in text
    assert "Durable billing and Stripe" in text
    assert "Provider ACL snapshots" in text
    assert "Evidence and docs" in text
    assert "follow-up autoplan" in phase_readme


def test_operations_evidence_log_tracks_unproven_staging_drills() -> None:
    text = Path(
        "docs/operations/evidence/2026-05-14-local-hardening-evidence.md"
    ).read_text(encoding="utf-8")

    assert "Environment: local" in text
    assert "Not staging evidence" in text
    assert "Restore Drill" in text
    assert "Rollback Drill" in text
    assert "Load Drill" in text
    assert "Cost Drill" in text
