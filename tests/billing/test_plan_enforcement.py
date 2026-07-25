from cortex.billing import (
    BillingStatus,
    InMemoryBillingRepository,
    PlanEnforcementService,
    SubscriptionStatus,
    UsageDimension,
)


def test_invite_only_default_blocks_source_creation_but_allows_reads() -> None:
    repo = InMemoryBillingRepository()
    service = PlanEnforcementService(repo)

    source_decision = service.decide(
        organization_id="org_1",
        dimension=UsageDimension.SOURCES,
    )
    retrieval_decision = service.decide(
        organization_id="org_1",
        dimension=UsageDimension.RETRIEVALS,
    )

    assert source_decision.allowed is False
    assert source_decision.reason == "plan_limit_exceeded"
    assert retrieval_decision.allowed is True


def test_active_trial_plan_enforces_usage_limit_and_records_usage() -> None:
    repo = InMemoryBillingRepository()
    customer = repo.ensure_customer(
        organization_id="org_1",
        status=BillingStatus.TRIALING,
    )
    repo.upsert_subscription(
        organization_id="org_1",
        billing_customer_id=customer.id,
        plan_id="free_trial",
        status=SubscriptionStatus.TRIALING,
    )
    repo.set_usage(
        organization_id="org_1",
        dimension=UsageDimension.SOURCES,
        quantity=2,
    )
    service = PlanEnforcementService(repo)

    allowed = service.enforce(
        organization_id="org_1",
        dimension=UsageDimension.SOURCES,
        requested_quantity=1,
    )
    denied = service.enforce(
        organization_id="org_1",
        dimension=UsageDimension.SOURCES,
        requested_quantity=1,
    )

    assert allowed.allowed is True
    assert allowed.remaining == 1
    assert denied.allowed is False
    assert denied.reason == "plan_limit_exceeded"
    assert repo.usage_quantity(
        organization_id="org_1",
        dimension=UsageDimension.SOURCES,
    ) == 3


def test_subscription_upsert_is_idempotent_for_provider_subscription() -> None:
    repo = InMemoryBillingRepository()
    customer = repo.ensure_customer(
        organization_id="org_1",
        provider_customer_id="cus_123",
        status=BillingStatus.ACTIVE,
    )

    first = repo.upsert_subscription(
        organization_id="org_1",
        billing_customer_id=customer.id,
        provider_subscription_id="sub_123",
        plan_id="free_trial",
        status=SubscriptionStatus.INCOMPLETE,
    )
    second = repo.upsert_subscription(
        organization_id="org_1",
        billing_customer_id=customer.id,
        provider_subscription_id="sub_123",
        plan_id="free_trial",
        status=SubscriptionStatus.ACTIVE,
    )

    assert first.id == second.id
    assert second.status == SubscriptionStatus.ACTIVE
    assert len(repo.subscriptions) == 1
