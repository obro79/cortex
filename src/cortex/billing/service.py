from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from cortex.billing.models import (
    BillingCustomer,
    BillingStatus,
    EntitlementDecision,
    PlanEntitlements,
    Subscription,
    SubscriptionStatus,
    UsageDimension,
    UsageMeter,
)
from cortex.ingestion.payloads import sha256_digest

FREE_TRIAL_ENTITLEMENTS = PlanEntitlements(
    plan_id="free_trial",
    limits={
        UsageDimension.SEATS: 5,
        UsageDimension.WORKSPACES: 1,
        UsageDimension.SOURCES: 3,
        UsageDimension.INDEXED_OBJECTS: 10_000,
        UsageDimension.RETRIEVALS: 1_000,
        UsageDimension.STORAGE_MB: 1_024,
        UsageDimension.MODEL_CALLS: 1_000,
    },
)

INVITE_ONLY_ENTITLEMENTS = PlanEntitlements(
    plan_id="invite_only",
    limits={
        UsageDimension.SEATS: 1,
        UsageDimension.WORKSPACES: 1,
        UsageDimension.SOURCES: 0,
        UsageDimension.INDEXED_OBJECTS: 0,
        UsageDimension.RETRIEVALS: 25,
        UsageDimension.STORAGE_MB: 0,
        UsageDimension.MODEL_CALLS: 0,
    },
)


class InMemoryBillingRepository:
    def __init__(self) -> None:
        self.customers: dict[str, BillingCustomer] = {}
        self.subscriptions: dict[str, Subscription] = {}
        self.usage: dict[tuple[str, UsageDimension], UsageMeter] = {}

    def ensure_customer(
        self,
        *,
        organization_id: str,
        provider: str = "stripe",
        provider_customer_id: str | None = None,
        status: BillingStatus = BillingStatus.INVITE_ONLY,
    ) -> BillingCustomer:
        now = datetime.now(UTC)
        customer_id = _stable_id("billcus", organization_id, provider)
        existing = self.customers.get(customer_id)
        if existing is not None:
            updated = replace(
                existing,
                provider_customer_id=provider_customer_id
                or existing.provider_customer_id,
                status=status,
                updated_at=now,
            )
            self.customers[customer_id] = updated
            return updated
        customer = BillingCustomer(
            id=customer_id,
            organization_id=organization_id,
            provider=provider,
            provider_customer_id=provider_customer_id,
            status=status,
            created_at=now,
            updated_at=now,
        )
        self.customers[customer.id] = customer
        return customer

    def upsert_subscription(
        self,
        *,
        organization_id: str,
        billing_customer_id: str,
        plan_id: str,
        status: SubscriptionStatus,
        provider_subscription_id: str | None = None,
        current_period_start: datetime | None = None,
        current_period_end: datetime | None = None,
    ) -> Subscription:
        now = datetime.now(UTC)
        subscription_id = _stable_id(
            "sub", organization_id, provider_subscription_id or plan_id
        )
        existing = self.subscriptions.get(subscription_id)
        created_at = existing.created_at if existing is not None else now
        subscription = Subscription(
            id=subscription_id,
            organization_id=organization_id,
            billing_customer_id=billing_customer_id,
            provider_subscription_id=provider_subscription_id,
            plan_id=plan_id,
            status=status,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            created_at=created_at,
            updated_at=now,
        )
        self.subscriptions[subscription.id] = subscription
        return subscription

    def active_subscription(self, organization_id: str) -> Subscription | None:
        candidates = [
            subscription
            for subscription in self.subscriptions.values()
            if subscription.organization_id == organization_id
            and subscription.status
            in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}
        ]
        return max(candidates, key=lambda item: item.updated_at, default=None)

    def set_usage(
        self,
        *,
        organization_id: str,
        dimension: UsageDimension,
        quantity: int,
    ) -> UsageMeter:
        if quantity < 0:
            raise ValueError("usage quantity must be non-negative")
        meter = UsageMeter(
            organization_id=organization_id,
            dimension=dimension,
            quantity=quantity,
        )
        self.usage[(organization_id, dimension)] = meter
        return meter

    def increment_usage(
        self,
        *,
        organization_id: str,
        dimension: UsageDimension,
        quantity: int = 1,
    ) -> UsageMeter:
        current = self.usage_quantity(
            organization_id=organization_id,
            dimension=dimension,
        )
        return self.set_usage(
            organization_id=organization_id,
            dimension=dimension,
            quantity=current + quantity,
        )

    def usage_quantity(
        self, *, organization_id: str, dimension: UsageDimension
    ) -> int:
        meter = self.usage.get((organization_id, dimension))
        return meter.quantity if meter is not None else 0


class PlanEnforcementService:
    def __init__(
        self,
        repository: InMemoryBillingRepository,
        *,
        entitlements: dict[str, PlanEntitlements] | None = None,
    ) -> None:
        self.repository = repository
        self.entitlements = entitlements or {
            FREE_TRIAL_ENTITLEMENTS.plan_id: FREE_TRIAL_ENTITLEMENTS,
            INVITE_ONLY_ENTITLEMENTS.plan_id: INVITE_ONLY_ENTITLEMENTS,
        }

    def entitlements_for(self, organization_id: str) -> PlanEntitlements:
        subscription = self.repository.active_subscription(organization_id)
        if subscription is None:
            return INVITE_ONLY_ENTITLEMENTS
        return self.entitlements.get(subscription.plan_id, INVITE_ONLY_ENTITLEMENTS)

    def decide(
        self,
        *,
        organization_id: str,
        dimension: UsageDimension,
        requested_quantity: int = 1,
    ) -> EntitlementDecision:
        if requested_quantity < 0:
            raise ValueError("requested quantity must be non-negative")
        entitlements = self.entitlements_for(organization_id)
        limit = entitlements.limit_for(dimension)
        current = self.repository.usage_quantity(
            organization_id=organization_id,
            dimension=dimension,
        )
        if limit is None:
            return EntitlementDecision(
                allowed=True,
                organization_id=organization_id,
                dimension=dimension,
                current_quantity=current,
                requested_quantity=requested_quantity,
                limit=None,
                reason="unlimited",
            )
        allowed = current + requested_quantity <= limit
        return EntitlementDecision(
            allowed=allowed,
            organization_id=organization_id,
            dimension=dimension,
            current_quantity=current,
            requested_quantity=requested_quantity,
            limit=limit,
            reason="allowed" if allowed else "plan_limit_exceeded",
        )

    def enforce(
        self,
        *,
        organization_id: str,
        dimension: UsageDimension,
        requested_quantity: int = 1,
    ) -> EntitlementDecision:
        decision = self.decide(
            organization_id=organization_id,
            dimension=dimension,
            requested_quantity=requested_quantity,
        )
        if not decision.allowed:
            return decision
        self.repository.increment_usage(
            organization_id=organization_id,
            dimension=dimension,
            quantity=requested_quantity,
        )
        return decision


def _stable_id(prefix: str, *parts: str) -> str:
    digest = sha256_digest(":".join(parts).encode()).removeprefix("sha256:")[:24]
    return f"{prefix}_{digest}"
