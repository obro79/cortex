from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class BillingStatus(StrEnum):
    INVITE_ONLY = "invite_only"
    TRIALING = "trialing"
    ACTIVE = "active"
    GRACE_PERIOD = "grace_period"
    PAST_DUE = "past_due"
    LOCKED = "locked"


class SubscriptionStatus(StrEnum):
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class UsageDimension(StrEnum):
    SEATS = "seats"
    WORKSPACES = "workspaces"
    SOURCES = "sources"
    INDEXED_OBJECTS = "indexed_objects"
    RETRIEVALS = "retrievals"
    STORAGE_MB = "storage_mb"
    MODEL_CALLS = "model_calls"


@dataclass(frozen=True)
class BillingCustomer:
    id: str
    organization_id: str
    provider: str
    provider_customer_id: str | None
    status: BillingStatus
    created_at: datetime
    updated_at: datetime
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Subscription:
    id: str
    organization_id: str
    billing_customer_id: str
    provider_subscription_id: str | None
    plan_id: str
    status: SubscriptionStatus
    current_period_start: datetime | None
    current_period_end: datetime | None
    created_at: datetime
    updated_at: datetime
    provider: str = "stripe"
    trial_start: datetime | None = None
    trial_end: datetime | None = None
    cancel_at: datetime | None = None
    canceled_at: datetime | None = None
    grace_period_ends_at: datetime | None = None
    provider_updated_at: datetime | None = None
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanEntitlements:
    plan_id: str
    limits: dict[UsageDimension, int | None]
    read_allowed_when_limited: bool = True

    def limit_for(self, dimension: UsageDimension) -> int | None:
        return self.limits.get(dimension)


@dataclass(frozen=True)
class UsageMeter:
    organization_id: str
    dimension: UsageDimension
    quantity: int
    period_start: datetime | None = None
    period_end: datetime | None = None


@dataclass(frozen=True)
class EntitlementDecision:
    allowed: bool
    organization_id: str
    dimension: UsageDimension
    current_quantity: int
    requested_quantity: int
    limit: int | None
    reason: str

    @property
    def remaining(self) -> int | None:
        if self.limit is None:
            return None
        return max(self.limit - self.current_quantity, 0)
