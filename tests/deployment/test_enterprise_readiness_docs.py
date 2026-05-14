from pathlib import Path

PHASE = Path("docs/phases/phase-22-enterprise-readiness")


def test_launch_checklist_declares_beta_status_and_blockers() -> None:
    text = (PHASE / "launch-checklist.md").read_text(encoding="utf-8")

    assert "invite-only beta" in text
    assert "Launch Blockers" in text
    assert "Complete Phase 15 onboarding routes" in text
    assert "Complete Stripe checkout" in text
    assert "Run staging restore, rollback, load, and cost drills" in text


def test_known_limitations_do_not_overclaim_enterprise_readiness() -> None:
    text = (PHASE / "known-limitations.md").read_text(encoding="utf-8")

    assert "not yet ready for unattended enterprise self-serve rollout" in text
    assert "provider-native per-user ACL parity is not claimed" in text
    assert "repository-level execution is not complete" in text


def test_sales_handoff_excludes_sensitive_support_intake() -> None:
    text = (PHASE / "sales-support-handoff.md").read_text(encoding="utf-8")

    assert "Do Not Promise" in text
    assert "Never request provider tokens" in text
    assert "raw private messages" in text
    assert "Trace ID" in text


def test_pricing_decision_stays_invite_only_until_billing_is_complete() -> None:
    text = (PHASE / "pricing-packaging-decision.md").read_text(encoding="utf-8")

    assert "invite-only beta packaging" in text
    assert "Stripe integration is not complete" in text
    assert "Read access remains available" in text
