from __future__ import annotations

import hmac
import json
from hashlib import sha256

import pytest

from cortex.billing import (
    InMemoryBillingRepository,
    StripeBillingService,
    StripeCheckoutRequest,
    StripePortalRequest,
    StripeSession,
    StripeWebhookVerificationError,
    SubscriptionStatus,
    verify_stripe_webhook,
)


class FakeStripeGateway:
    async def create_checkout_session(
        self, request: StripeCheckoutRequest
    ) -> StripeSession:
        return StripeSession(
            id="cs_test",
            url=request.success_url,
            provider_customer_id=request.provider_customer_id,
            provider_subscription_id="sub_test",
        )

    async def create_portal_session(
        self, request: StripePortalRequest
    ) -> StripeSession:
        return StripeSession(
            id="bps_test",
            url=request.return_url,
            provider_customer_id=request.provider_customer_id,
        )


def test_verify_stripe_webhook_rejects_bad_signature() -> None:
    payload = b'{"id":"evt_1","type":"checkout.session.completed"}'

    with pytest.raises(StripeWebhookVerificationError):
        verify_stripe_webhook(
            payload=payload,
            signature_header="t=1700000000,v1=bad",
            secret="whsec_test",
            now=1700000000,
        )


async def test_stripe_webhook_updates_subscription_once() -> None:
    repo = InMemoryBillingRepository()
    service = StripeBillingService(
        repository=repo,
        gateway=FakeStripeGateway(),
        webhook_secret="whsec_test",
        tolerance_seconds=10_000_000_000,
    )
    payload = json.dumps(
        {
            "id": "evt_checkout",
            "type": "checkout.session.completed",
            "created": 1700000000,
            "data": {
                "object": {
                    "id": "cs_test",
                    "customer": "cus_test",
                    "subscription": "sub_test",
                    "created": 1700000000,
                    "metadata": {
                        "organization_id": "org_1",
                        "plan_id": "free_trial",
                    },
                }
            },
        },
        separators=(",", ":"),
    ).encode()
    signature = _signature(payload)

    first = await service.handle_webhook(
        payload=payload,
        signature_header=signature,
    )
    second = await service.handle_webhook(
        payload=payload,
        signature_header=signature,
    )

    assert first.status == "processed"
    assert first.organization_id == "org_1"
    assert second.duplicate is True
    assert len(repo.webhook_events) == 1
    assert repo.active_subscription("org_1") is not None
    assert repo.active_subscription("org_1").status == SubscriptionStatus.ACTIVE


def _signature(payload: bytes, *, timestamp: int = 1700000000) -> str:
    expected = hmac.new(
        b"whsec_test",
        f"{timestamp}.{payload.decode()}".encode(),
        sha256,
    ).hexdigest()
    return f"t={timestamp},v1={expected}"
