from __future__ import annotations

import hmac
import json
from dataclasses import replace
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.auth.dependencies import AUTH_EMAIL_HEADER
from cortex.billing import (
    BillingStatus,
    InMemoryBillingRepository,
    StripeBillingService,
    StripeCheckoutRequest,
    StripePortalRequest,
    StripeSession,
    StripeWebhookVerificationError,
    SubscriptionStatus,
    verify_stripe_webhook,
)
from cortex.config import Settings
from cortex.tenancy import MembershipRole
from cortex.ui.auth import WORKSPACE_ID_HEADER


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


def test_billing_checkout_and_portal_routes_require_billing_admin() -> None:
    app = create_app(
        Settings(
            cortex_public_auth_enabled=True,
            stripe_webhook_secret="whsec_test",
            stripe_price_id="price_test",
            stripe_success_url="https://example.test/success",
            stripe_cancel_url="https://example.test/cancel",
            stripe_portal_return_url="https://example.test/billing",
        )
    )
    app.state.stripe_billing_service = StripeBillingService(
        repository=app.state.billing_repository,
        gateway=FakeStripeGateway(),
        webhook_secret="whsec_test",
        tolerance_seconds=10_000_000_000,
    )
    headers = _seed_owner(app)
    client = TestClient(app)

    checkout = client.post("/billing/checkout", json={}, headers=headers)
    customer = app.state.billing_repository.ensure_customer(
        organization_id=next(iter(app.state.tenant_repository.organizations)),
        provider_customer_id="cus_test",
        status=BillingStatus.ACTIVE,
    )
    assert customer.provider_customer_id == "cus_test"
    portal = client.post("/billing/portal", json={}, headers=headers)

    assert checkout.status_code == 200
    assert checkout.json()["id"] == "cs_test"
    assert portal.status_code == 200
    assert portal.json()["id"] == "bps_test"


def test_billing_checkout_denies_non_billing_admin() -> None:
    app = create_app(
        Settings(
            cortex_public_auth_enabled=True,
            stripe_webhook_secret="whsec_test",
            stripe_price_id="price_test",
            stripe_success_url="https://example.test/success",
            stripe_cancel_url="https://example.test/cancel",
        )
    )
    app.state.stripe_billing_service = StripeBillingService(
        repository=app.state.billing_repository,
        gateway=FakeStripeGateway(),
        webhook_secret="whsec_test",
        tolerance_seconds=10_000_000_000,
    )
    headers = _seed_member(app, role=MembershipRole.MEMBER)

    response = TestClient(app).post("/billing/checkout", json={}, headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "missing_permission"


def test_stripe_webhook_route_verifies_signature_and_records_event() -> None:
    app = create_app(Settings(stripe_webhook_secret="whsec_test"))
    app.state.stripe_billing_service = StripeBillingService(
        repository=app.state.billing_repository,
        gateway=FakeStripeGateway(),
        webhook_secret="whsec_test",
        tolerance_seconds=10_000_000_000,
    )
    payload = json.dumps(
        {
            "id": "evt_route",
            "type": "checkout.session.completed",
            "created": 1700000000,
            "data": {
                "object": {
                    "id": "cs_route",
                    "customer": "cus_route",
                    "subscription": "sub_route",
                    "metadata": {"organization_id": "org_route"},
                }
            },
        },
        separators=(",", ":"),
    ).encode()

    response = TestClient(app).post(
        "/billing/webhooks/stripe",
        content=payload,
        headers={"stripe-signature": _signature(payload)},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert len(app.state.billing_repository.webhook_events) == 1


def _signature(payload: bytes, *, timestamp: int = 1700000000) -> str:
    expected = hmac.new(
        b"whsec_test",
        f"{timestamp}.{payload.decode()}".encode(),
        sha256,
    ).hexdigest()
    return f"t={timestamp},v1={expected}"


def _seed_owner(app: object) -> dict[str, str]:
    return _seed_member(app, role=MembershipRole.OWNER)


def _seed_member(app: object, *, role: MembershipRole) -> dict[str, str]:
    repo = app.state.tenant_repository
    user = repo.upsert_user(
        auth_provider="local",
        auth_subject="owner@example.com",
        email="owner@example.com",
    )
    _, workspace, _ = repo.create_organization_with_workspace(
        user_id=user.id,
        organization_name="Acme",
        workspace_name="Engineering",
        workspace_slug="engineering",
    )
    membership_id = next(iter(repo.memberships))
    repo.memberships[membership_id] = replace(
        repo.memberships[membership_id],
        role=role,
    )
    return {
        AUTH_EMAIL_HEADER: "owner@example.com",
        WORKSPACE_ID_HEADER: workspace.id,
    }
