from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from cortex.db.models import (
    BillingCustomerRecord,
    BillingSubscriptionRecord,
    BillingUsageMeterRecord,
    BillingWebhookEventRecord,
)
from cortex.ingestion.payloads import sha256_digest
from cortex.utils.asyncio import maybe_await

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
        self.webhook_events: dict[str, dict[str, object]] = {}

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
        provider: str = "stripe",
        current_period_start: datetime | None = None,
        current_period_end: datetime | None = None,
        provider_updated_at: datetime | None = None,
        metadata_json: dict[str, object] | None = None,
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
            provider=provider,
            provider_updated_at=provider_updated_at,
            metadata_json=metadata_json or {},
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

    def usage_quantity(self, *, organization_id: str, dimension: UsageDimension) -> int:
        meter = self.usage.get((organization_id, dimension))
        return meter.quantity if meter is not None else 0

    def record_webhook_event(
        self,
        *,
        provider_event_id: str,
        event_type: str,
        payload_hash: str,
        status: str,
        signature_status: str = "verified",
        provider: str = "stripe",
        object_id: str | None = None,
        provider_created_at: datetime | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> tuple[bool, dict[str, object]]:
        record_id = _stable_id("billwh", provider, provider_event_id)
        existing = self.webhook_events.get(record_id)
        if existing is not None:
            return False, existing
        record: dict[str, object] = {
            "id": record_id,
            "provider": provider,
            "provider_event_id": provider_event_id,
            "event_type": event_type,
            "object_id": object_id,
            "signature_status": signature_status,
            "status": status,
            "provider_created_at": provider_created_at,
            "received_at": datetime.now(UTC),
            "payload_hash": payload_hash,
            "metadata_json": metadata_json or {},
        }
        self.webhook_events[record_id] = record
        return True, record


class BillingRepository(Protocol):
    def ensure_customer(
        self,
        *,
        organization_id: str,
        provider: str = "stripe",
        provider_customer_id: str | None = None,
        status: BillingStatus = BillingStatus.INVITE_ONLY,
    ) -> BillingCustomer | Awaitable[BillingCustomer]: ...

    def upsert_subscription(
        self,
        *,
        organization_id: str,
        billing_customer_id: str,
        plan_id: str,
        status: SubscriptionStatus,
        provider_subscription_id: str | None = None,
        provider: str = "stripe",
        current_period_start: datetime | None = None,
        current_period_end: datetime | None = None,
        provider_updated_at: datetime | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> Subscription | Awaitable[Subscription]: ...

    def active_subscription(
        self, organization_id: str
    ) -> Subscription | None | Awaitable[Subscription | None]: ...

    def set_usage(
        self,
        *,
        organization_id: str,
        dimension: UsageDimension,
        quantity: int,
    ) -> UsageMeter | Awaitable[UsageMeter]: ...

    def increment_usage(
        self,
        *,
        organization_id: str,
        dimension: UsageDimension,
        quantity: int = 1,
    ) -> UsageMeter | Awaitable[UsageMeter]: ...

    def usage_quantity(
        self, *, organization_id: str, dimension: UsageDimension
    ) -> int | Awaitable[int]: ...


class SqlAlchemyBillingRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def ensure_customer(
        self,
        *,
        organization_id: str,
        provider: str = "stripe",
        provider_customer_id: str | None = None,
        status: BillingStatus = BillingStatus.INVITE_ONLY,
    ) -> BillingCustomer:
        now = datetime.now(UTC)
        customer_id = _stable_id("billcus", organization_id, provider)
        async with self.session_factory() as session:
            record = await session.get(BillingCustomerRecord, customer_id)
            if record is None:
                record = BillingCustomerRecord(
                    id=customer_id,
                    organization_id=organization_id,
                    provider=provider,
                    provider_customer_id=provider_customer_id,
                    status=BillingStatus(status).value,
                    metadata_json={},
                    created_at=now,
                    updated_at=now,
                )
                session.add(record)
            else:
                record.provider_customer_id = (
                    provider_customer_id or record.provider_customer_id
                )
                record.status = BillingStatus(status).value
                record.updated_at = now
            await session.commit()
            await session.refresh(record)
            return billing_customer_from_record(record)

    async def upsert_subscription(
        self,
        *,
        organization_id: str,
        billing_customer_id: str,
        plan_id: str,
        status: SubscriptionStatus,
        provider_subscription_id: str | None = None,
        provider: str = "stripe",
        current_period_start: datetime | None = None,
        current_period_end: datetime | None = None,
        provider_updated_at: datetime | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> Subscription:
        now = datetime.now(UTC)
        subscription_id = _stable_id(
            "sub", organization_id, provider_subscription_id or plan_id
        )
        async with self.session_factory() as session:
            record = await session.get(BillingSubscriptionRecord, subscription_id)
            if record is None:
                record = BillingSubscriptionRecord(
                    id=subscription_id,
                    organization_id=organization_id,
                    billing_customer_id=billing_customer_id,
                    provider=provider,
                    provider_subscription_id=provider_subscription_id,
                    plan_id=plan_id,
                    status=SubscriptionStatus(status).value,
                    current_period_start=current_period_start,
                    current_period_end=current_period_end,
                    provider_updated_at=provider_updated_at,
                    metadata_json=metadata_json or {},
                    created_at=now,
                    updated_at=now,
                )
                session.add(record)
            else:
                if (
                    provider_updated_at is not None
                    and record.provider_updated_at is not None
                    and provider_updated_at < record.provider_updated_at
                ):
                    return subscription_from_record(record)
                record.billing_customer_id = billing_customer_id
                record.provider = provider
                record.provider_subscription_id = provider_subscription_id
                record.plan_id = plan_id
                record.status = SubscriptionStatus(status).value
                record.current_period_start = current_period_start
                record.current_period_end = current_period_end
                record.provider_updated_at = provider_updated_at
                record.metadata_json = metadata_json or {}
                record.updated_at = now
            await session.commit()
            await session.refresh(record)
            return subscription_from_record(record)

    async def active_subscription(self, organization_id: str) -> Subscription | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(BillingSubscriptionRecord).where(
                    BillingSubscriptionRecord.organization_id == organization_id,
                    BillingSubscriptionRecord.status.in_(
                        [
                            SubscriptionStatus.ACTIVE.value,
                            SubscriptionStatus.TRIALING.value,
                        ]
                    ),
                )
            )
            candidates = [
                subscription_from_record(record) for record in result.scalars()
            ]
        return max(candidates, key=lambda item: item.updated_at, default=None)

    async def set_usage(
        self,
        *,
        organization_id: str,
        dimension: UsageDimension,
        quantity: int,
    ) -> UsageMeter:
        if quantity < 0:
            raise ValueError("usage quantity must be non-negative")
        period_key = "current"
        record_id = _stable_id(
            "usage",
            organization_id,
            UsageDimension(dimension).value,
        )
        now = datetime.now(UTC)
        async with self.session_factory() as session:
            record = await session.get(BillingUsageMeterRecord, record_id)
            if record is None:
                record = BillingUsageMeterRecord(
                    id=record_id,
                    organization_id=organization_id,
                    dimension=UsageDimension(dimension).value,
                    period_key=period_key,
                    quantity=quantity,
                    created_at=now,
                    updated_at=now,
                )
                session.add(record)
            else:
                record.quantity = quantity
                record.updated_at = now
            await session.commit()
            await session.refresh(record)
            return usage_meter_from_record(record)

    async def increment_usage(
        self,
        *,
        organization_id: str,
        dimension: UsageDimension,
        quantity: int = 1,
    ) -> UsageMeter:
        current = await self.usage_quantity(
            organization_id=organization_id,
            dimension=dimension,
        )
        return await self.set_usage(
            organization_id=organization_id,
            dimension=dimension,
            quantity=current + quantity,
        )

    async def usage_quantity(
        self, *, organization_id: str, dimension: UsageDimension
    ) -> int:
        record_id = _stable_id(
            "usage",
            organization_id,
            UsageDimension(dimension).value,
        )
        async with self.session_factory() as session:
            record = await session.get(BillingUsageMeterRecord, record_id)
            return int(record.quantity) if record is not None else 0

    async def record_webhook_event(
        self,
        *,
        provider_event_id: str,
        event_type: str,
        payload_hash: str,
        status: str,
        signature_status: str = "verified",
        provider: str = "stripe",
        object_id: str | None = None,
        provider_created_at: datetime | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> tuple[bool, BillingWebhookEventRecord]:
        now = datetime.now(UTC)
        record_id = _stable_id("billwh", provider, provider_event_id)
        async with self.session_factory() as session:
            record = await session.get(BillingWebhookEventRecord, record_id)
            if record is not None:
                return False, record
            record = BillingWebhookEventRecord(
                id=record_id,
                provider=provider,
                provider_event_id=provider_event_id,
                event_type=event_type,
                object_id=object_id,
                signature_status=signature_status,
                status=status,
                provider_created_at=provider_created_at,
                received_at=now,
                payload_hash=payload_hash,
                metadata_json=metadata_json or {},
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return True, record


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


class AsyncPlanEnforcementService:
    def __init__(
        self,
        repository: BillingRepository,
        *,
        entitlements: dict[str, PlanEntitlements] | None = None,
    ) -> None:
        self.repository = repository
        self.entitlements = entitlements or {
            FREE_TRIAL_ENTITLEMENTS.plan_id: FREE_TRIAL_ENTITLEMENTS,
            INVITE_ONLY_ENTITLEMENTS.plan_id: INVITE_ONLY_ENTITLEMENTS,
        }

    async def entitlements_for(self, organization_id: str) -> PlanEntitlements:
        subscription = await maybe_await(
            self.repository.active_subscription(organization_id)
        )
        if subscription is None:
            return INVITE_ONLY_ENTITLEMENTS
        return self.entitlements.get(subscription.plan_id, INVITE_ONLY_ENTITLEMENTS)

    async def decide(
        self,
        *,
        organization_id: str,
        dimension: UsageDimension,
        requested_quantity: int = 1,
    ) -> EntitlementDecision:
        if requested_quantity < 0:
            raise ValueError("requested quantity must be non-negative")
        entitlements = await self.entitlements_for(organization_id)
        limit = entitlements.limit_for(dimension)
        current = await maybe_await(
            self.repository.usage_quantity(
                organization_id=organization_id,
                dimension=dimension,
            )
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

    async def enforce(
        self,
        *,
        organization_id: str,
        dimension: UsageDimension,
        requested_quantity: int = 1,
    ) -> EntitlementDecision:
        decision = await self.decide(
            organization_id=organization_id,
            dimension=dimension,
            requested_quantity=requested_quantity,
        )
        if not decision.allowed:
            return decision
        await maybe_await(
            self.repository.increment_usage(
                organization_id=organization_id,
                dimension=dimension,
                quantity=requested_quantity,
            )
        )
        return decision


def billing_customer_from_record(record: BillingCustomerRecord) -> BillingCustomer:
    return BillingCustomer(
        id=record.id,
        organization_id=record.organization_id,
        provider=record.provider,
        provider_customer_id=record.provider_customer_id,
        status=BillingStatus(record.status),
        metadata_json=dict(record.metadata_json),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def subscription_from_record(record: BillingSubscriptionRecord) -> Subscription:
    return Subscription(
        id=record.id,
        organization_id=record.organization_id,
        billing_customer_id=record.billing_customer_id,
        provider_subscription_id=record.provider_subscription_id,
        plan_id=record.plan_id,
        status=SubscriptionStatus(record.status),
        current_period_start=record.current_period_start,
        current_period_end=record.current_period_end,
        created_at=record.created_at,
        updated_at=record.updated_at,
        provider=record.provider,
        trial_start=record.trial_start,
        trial_end=record.trial_end,
        cancel_at=record.cancel_at,
        canceled_at=record.canceled_at,
        grace_period_ends_at=record.grace_period_ends_at,
        provider_updated_at=record.provider_updated_at,
        metadata_json=dict(record.metadata_json),
    )


def usage_meter_from_record(record: BillingUsageMeterRecord) -> UsageMeter:
    return UsageMeter(
        organization_id=record.organization_id,
        dimension=UsageDimension(record.dimension),
        quantity=record.quantity,
        period_start=record.period_start,
        period_end=record.period_end,
    )


def _stable_id(prefix: str, *parts: str) -> str:
    digest = sha256_digest(":".join(parts).encode()).removeprefix("sha256:")[:24]
    return f"{prefix}_{digest}"
