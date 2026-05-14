from __future__ import annotations

import hmac
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol, cast

import httpx

from cortex.billing.models import BillingStatus, SubscriptionStatus
from cortex.billing.service import BillingRepository
from cortex.ingestion.payloads import sha256_digest
from cortex.utils.asyncio import maybe_await


class StripeWebhookVerificationError(ValueError):
    pass


@dataclass(frozen=True)
class StripeCheckoutRequest:
    organization_id: str
    billing_customer_id: str
    provider_customer_id: str | None
    price_id: str
    success_url: str
    cancel_url: str
    plan_id: str = "free_trial"
    trial_period_days: int | None = None
    metadata_json: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StripePortalRequest:
    provider_customer_id: str
    return_url: str


@dataclass(frozen=True)
class StripeSession:
    id: str
    url: str
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None


@dataclass(frozen=True)
class StripeWebhookResult:
    provider_event_id: str
    event_type: str
    status: str
    duplicate: bool = False
    organization_id: str | None = None


class StripeGateway(Protocol):
    async def create_checkout_session(
        self, request: StripeCheckoutRequest
    ) -> StripeSession: ...

    async def create_portal_session(
        self, request: StripePortalRequest
    ) -> StripeSession: ...


class HttpStripeGateway:
    def __init__(
        self, *, api_key: str, base_url: str = "https://api.stripe.com"
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def create_checkout_session(
        self, request: StripeCheckoutRequest
    ) -> StripeSession:
        data: dict[str, str] = {
            "mode": "subscription",
            "line_items[0][price]": request.price_id,
            "line_items[0][quantity]": "1",
            "success_url": request.success_url,
            "cancel_url": request.cancel_url,
            "client_reference_id": request.organization_id,
            "metadata[organization_id]": request.organization_id,
            "metadata[billing_customer_id]": request.billing_customer_id,
            "metadata[plan_id]": request.plan_id,
        }
        if request.provider_customer_id:
            data["customer"] = request.provider_customer_id
        if request.trial_period_days is not None:
            data["subscription_data[trial_period_days]"] = str(
                request.trial_period_days
            )
        for key, value in request.metadata_json.items():
            data[f"metadata[{key}]"] = value
        payload = await self._post("/v1/checkout/sessions", data)
        return StripeSession(
            id=str(payload["id"]),
            url=str(payload["url"]),
            provider_customer_id=_optional_str(payload.get("customer")),
            provider_subscription_id=_optional_str(payload.get("subscription")),
        )

    async def create_portal_session(
        self, request: StripePortalRequest
    ) -> StripeSession:
        payload = await self._post(
            "/v1/billing_portal/sessions",
            {
                "customer": request.provider_customer_id,
                "return_url": request.return_url,
            },
        )
        return StripeSession(
            id=str(payload["id"]),
            url=str(payload["url"]),
            provider_customer_id=request.provider_customer_id,
        )

    async def _post(self, path: str, data: Mapping[str, str]) -> dict[str, object]:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10.0,
        ) as client:
            response = await client.post(path, data=data)
        response.raise_for_status()
        return cast(dict[str, object], response.json())


class StripeBillingService:
    def __init__(
        self,
        *,
        repository: BillingRepository,
        gateway: StripeGateway,
        webhook_secret: str,
        tolerance_seconds: int = 300,
    ) -> None:
        self.repository = repository
        self.gateway = gateway
        self.webhook_secret = webhook_secret
        self.tolerance_seconds = tolerance_seconds

    async def create_checkout_session(
        self, request: StripeCheckoutRequest
    ) -> StripeSession:
        return await self.gateway.create_checkout_session(request)

    async def create_portal_session(
        self, request: StripePortalRequest
    ) -> StripeSession:
        return await self.gateway.create_portal_session(request)

    async def handle_webhook(
        self, *, payload: bytes, signature_header: str
    ) -> StripeWebhookResult:
        event = verify_stripe_webhook(
            payload=payload,
            signature_header=signature_header,
            secret=self.webhook_secret,
            tolerance_seconds=self.tolerance_seconds,
        )
        provider_event_id = str(event.get("id", ""))
        event_type = str(event.get("type", ""))
        data = _dict(event.get("data"))
        obj = _dict(data.get("object"))
        object_id = _optional_str(obj.get("id"))
        payload_hash = sha256_digest(payload)
        record_method = getattr(self.repository, "record_webhook_event", None)
        if record_method is not None:
            inserted, _ = await maybe_await(
                record_method(
                    provider_event_id=provider_event_id,
                    event_type=event_type,
                    payload_hash=payload_hash,
                    status="received",
                    signature_status="verified",
                    object_id=object_id,
                    provider_created_at=_stripe_timestamp(event.get("created")),
                    metadata_json={"api_version": str(event.get("api_version", ""))},
                )
            )
            if not inserted:
                return StripeWebhookResult(
                    provider_event_id=provider_event_id,
                    event_type=event_type,
                    status="duplicate",
                    duplicate=True,
                )
        organization_id = await self._apply_webhook_event(event_type, obj)
        return StripeWebhookResult(
            provider_event_id=provider_event_id,
            event_type=event_type,
            status="processed",
            organization_id=organization_id,
        )

    async def _apply_webhook_event(
        self, event_type: str, obj: dict[str, object]
    ) -> str | None:
        if event_type == "checkout.session.completed":
            metadata = _dict(obj.get("metadata"))
            organization_id = _optional_str(metadata.get("organization_id"))
            plan_id = _optional_str(metadata.get("plan_id")) or "free_trial"
            provider_customer_id = _optional_str(obj.get("customer"))
            provider_subscription_id = _optional_str(obj.get("subscription"))
            if organization_id is None or provider_customer_id is None:
                return organization_id
            customer = await maybe_await(
                self.repository.ensure_customer(
                    organization_id=organization_id,
                    provider_customer_id=provider_customer_id,
                    status=BillingStatus.ACTIVE,
                )
            )
            await maybe_await(
                self.repository.upsert_subscription(
                    organization_id=organization_id,
                    billing_customer_id=customer.id,
                    provider_subscription_id=provider_subscription_id,
                    plan_id=plan_id,
                    status=SubscriptionStatus.ACTIVE,
                    provider_updated_at=_stripe_timestamp(obj.get("created")),
                    metadata_json=dict(metadata),
                )
            )
            return organization_id
        if event_type.startswith("customer.subscription."):
            metadata = _dict(obj.get("metadata"))
            organization_id = _optional_str(metadata.get("organization_id"))
            billing_customer_id = _optional_str(metadata.get("billing_customer_id"))
            if organization_id is None or billing_customer_id is None:
                return organization_id
            await maybe_await(
                self.repository.upsert_subscription(
                    organization_id=organization_id,
                    billing_customer_id=billing_customer_id,
                    provider_subscription_id=_optional_str(obj.get("id")),
                    plan_id=_optional_str(metadata.get("plan_id")) or "free_trial",
                    status=_subscription_status(obj),
                    current_period_start=_stripe_timestamp(
                        obj.get("current_period_start")
                    ),
                    current_period_end=_stripe_timestamp(obj.get("current_period_end")),
                    provider_updated_at=_stripe_timestamp(obj.get("created")),
                    metadata_json=dict(metadata),
                )
            )
            return organization_id
        return None


def verify_stripe_webhook(
    *,
    payload: bytes,
    signature_header: str,
    secret: str,
    tolerance_seconds: int = 300,
    now: int | None = None,
) -> dict[str, object]:
    if not secret:
        raise StripeWebhookVerificationError("stripe_webhook_secret_missing")
    timestamp, signatures = _parse_signature_header(signature_header)
    current = int(time.time() if now is None else now)
    if abs(current - timestamp) > tolerance_seconds:
        raise StripeWebhookVerificationError("stripe_webhook_timestamp_out_of_range")
    signed_payload = f"{timestamp}.{payload.decode()}".encode()
    expected = hmac.new(secret.encode(), signed_payload, sha256).hexdigest()
    if not any(hmac.compare_digest(expected, signature) for signature in signatures):
        raise StripeWebhookVerificationError("stripe_webhook_signature_mismatch")
    decoded = json.loads(payload.decode())
    if not isinstance(decoded, dict):
        raise StripeWebhookVerificationError("stripe_webhook_payload_invalid")
    return cast(dict[str, object], decoded)


def _parse_signature_header(header: str) -> tuple[int, list[str]]:
    values: dict[str, list[str]] = {}
    for part in header.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        values.setdefault(key, []).append(value)
    timestamps = values.get("t") or []
    signatures = values.get("v1") or []
    if not timestamps or not signatures:
        raise StripeWebhookVerificationError("stripe_webhook_signature_missing")
    try:
        timestamp = int(timestamps[0])
    except ValueError as error:
        raise StripeWebhookVerificationError(
            "stripe_webhook_timestamp_invalid"
        ) from error
    return timestamp, signatures


def _subscription_status(obj: dict[str, object]) -> SubscriptionStatus:
    raw = str(obj.get("status", "active"))
    try:
        return SubscriptionStatus(raw)
    except ValueError:
        return SubscriptionStatus.ACTIVE


def _stripe_timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, (str, bytes, bytearray, int, float)):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def _dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None
