from __future__ import annotations

import argparse
import asyncio
import hmac
import json
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from cortex.billing import (
    InMemoryBillingRepository,
    StripeBillingService,
    StripeCheckoutRequest,
    StripePortalRequest,
    StripeSession,
)


@dataclass(frozen=True)
class SmokeCommand:
    name: str
    description: str


class FakeStripeGateway:
    def __init__(self) -> None:
        self.checkout_requests: list[StripeCheckoutRequest] = []
        self.portal_requests: list[StripePortalRequest] = []

    async def create_checkout_session(
        self, request: StripeCheckoutRequest
    ) -> StripeSession:
        self.checkout_requests.append(request)
        return StripeSession(
            id="cs_test_static",
            url="https://checkout.stripe.test/session",
            provider_customer_id=request.provider_customer_id or "cus_test_static",
            provider_subscription_id="sub_test_static",
        )

    async def create_portal_session(
        self, request: StripePortalRequest
    ) -> StripeSession:
        self.portal_requests.append(request)
        return StripeSession(
            id="bps_test_static",
            url="https://billing.stripe.test/session",
            provider_customer_id=request.provider_customer_id,
        )


def smoke_commands() -> list[SmokeCommand]:
    return [
        SmokeCommand(
            "static runbook",
            (
                "Verify Stripe activation runbook routes, evidence fields, "
                "and secret names."
            ),
        ),
        SmokeCommand(
            "fake gateway",
            "Create checkout/portal sessions and replay a signed webhook locally.",
        ),
    ]


def static_smoke() -> None:
    runbook = Path("docs/runbooks/stripe-production-activation.md").read_text()
    required = [
        "STRIPE_API_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "STRIPE_PRICE_ID",
        "/billing/checkout",
        "/billing/portal",
        "/billing/webhooks/stripe",
        "Do not record live secrets",
        "raw webhook payload",
    ]
    missing = [item for item in required if item not in runbook]
    if missing:
        raise RuntimeError(f"stripe activation runbook missing: {', '.join(missing)}")


async def fake_gateway_smoke() -> dict[str, object]:
    repository = InMemoryBillingRepository()
    gateway = FakeStripeGateway()
    service = StripeBillingService(
        repository=repository,
        gateway=gateway,
        webhook_secret="whsec_static",
    )
    customer = repository.ensure_customer(
        organization_id="org_static",
        provider_customer_id="cus_test_static",
    )
    checkout = await service.create_checkout_session(
        StripeCheckoutRequest(
            organization_id="org_static",
            billing_customer_id=customer.id,
            provider_customer_id=customer.provider_customer_id,
            price_id="price_static",
            success_url="https://example.test/success",
            cancel_url="https://example.test/cancel",
            metadata_json={"workspace_id": "ws_static"},
        )
    )
    portal = await service.create_portal_session(
        StripePortalRequest(
            provider_customer_id="cus_test_static",
            return_url="https://example.test/billing",
        )
    )
    payload = json.dumps(
        {
            "id": "evt_static_checkout",
            "type": "checkout.session.completed",
            "created": int(time.time()),
            "data": {
                "object": {
                    "id": "cs_static",
                    "customer": "cus_test_static",
                    "subscription": "sub_static",
                    "metadata": {
                        "organization_id": "org_static",
                        "billing_customer_id": customer.id,
                        "plan_id": "free_trial",
                    },
                }
            },
        },
        separators=(",", ":"),
    ).encode()
    signature = _signature(payload, secret="whsec_static")
    first = await service.handle_webhook(
        payload=payload,
        signature_header=signature,
    )
    second = await service.handle_webhook(
        payload=payload,
        signature_header=signature,
    )
    if first.status != "processed" or not second.duplicate:
        raise RuntimeError("stripe webhook replay did not process then dedupe")
    return {
        "checkout_session_prefix": checkout.id.split("_", 2)[0],
        "portal_session_prefix": portal.id.split("_", 2)[0],
        "first_webhook_status": first.status,
        "second_webhook_status": second.status,
        "webhook_duplicate": second.duplicate,
        "recorded_webhook_events": len(repository.webhook_events),
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run no-secret Stripe production activation smoke checks."
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help="Validate the Stripe activation runbook.",
    )
    parser.add_argument(
        "--fake-gateway",
        action="store_true",
        help="Run local checkout, portal, and signed webhook replay checks.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print planned smoke checks without executing them.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.list:
        for command in smoke_commands():
            print(f"{command.name}: {command.description}")
        return 0
    try:
        if args.static:
            static_smoke()
        if args.fake_gateway:
            result = asyncio.run(fake_gateway_smoke())
            print(json.dumps(result, sort_keys=True))
        if not args.static and not args.fake_gateway:
            static_smoke()
            result = asyncio.run(fake_gateway_smoke())
            print(json.dumps(result, sort_keys=True))
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


def _signature(payload: bytes, *, secret: str) -> str:
    timestamp = int(time.time())
    digest = hmac.new(
        secret.encode(),
        f"{timestamp}.{payload.decode()}".encode(),
        sha256,
    )
    return f"t={timestamp},v1={digest.hexdigest()}"


if __name__ == "__main__":
    raise SystemExit(main())
