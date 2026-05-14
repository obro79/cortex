from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from cortex.auth.dependencies import require_permission, require_tenant_context
from cortex.billing import (
    BillingStatus,
    StripeBillingService,
    StripeCheckoutRequest,
    StripePortalRequest,
    StripeWebhookVerificationError,
)
from cortex.config import Settings
from cortex.tenancy import TenantContext
from cortex.tenancy.rbac import Permission
from cortex.utils.asyncio import maybe_await

router = APIRouter(prefix="/billing", tags=["billing"])
TENANT_CONTEXT_DEPENDENCY = Depends(require_tenant_context)


@router.post("/checkout")
async def create_checkout(
    request: Request,
    body: dict[str, Any],
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=context.workspace_id,
        permission=Permission.BILLING_ADMIN,
    )
    settings = _settings(request)
    service = _stripe_billing_service(request)
    price_id = str(body.get("price_id") or settings.stripe_price_id)
    success_url = str(body.get("success_url") or settings.stripe_success_url)
    cancel_url = str(body.get("cancel_url") or settings.stripe_cancel_url)
    if not price_id or not success_url or not cancel_url:
        raise HTTPException(status_code=422, detail="stripe checkout is not configured")
    customer = await maybe_await(
        service.repository.ensure_customer(
            organization_id=context.organization_id,
            status=BillingStatus.TRIALING,
        )
    )
    session = await service.create_checkout_session(
        StripeCheckoutRequest(
            organization_id=context.organization_id,
            billing_customer_id=customer.id,
            provider_customer_id=customer.provider_customer_id,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            plan_id=str(body.get("plan_id") or "free_trial"),
            metadata_json={
                "workspace_id": context.workspace_id,
                "requested_by_user_id": context.user_id,
            },
        )
    )
    return {
        "id": session.id,
        "url": session.url,
        "provider_customer_id": session.provider_customer_id,
    }


@router.post("/portal")
async def create_portal(
    request: Request,
    body: dict[str, Any],
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=context.workspace_id,
        permission=Permission.BILLING_ADMIN,
    )
    settings = _settings(request)
    service = _stripe_billing_service(request)
    return_url = str(body.get("return_url") or settings.stripe_portal_return_url)
    if not return_url:
        raise HTTPException(status_code=422, detail="stripe portal is not configured")
    customer = await maybe_await(
        service.repository.ensure_customer(
            organization_id=context.organization_id,
            status=BillingStatus.ACTIVE,
        )
    )
    if not customer.provider_customer_id:
        raise HTTPException(status_code=409, detail="stripe_customer_missing")
    session = await service.create_portal_session(
        StripePortalRequest(
            provider_customer_id=customer.provider_customer_id,
            return_url=return_url,
        )
    )
    return {"id": session.id, "url": session.url}


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default="", alias="stripe-signature"),
) -> dict[str, object]:
    service = _stripe_billing_service(request)
    try:
        result = await service.handle_webhook(
            payload=await request.body(),
            signature_header=stripe_signature,
        )
    except StripeWebhookVerificationError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    return {
        "ok": True,
        "status": result.status,
        "duplicate": result.duplicate,
        "event_type": result.event_type,
        "organization_id": result.organization_id,
    }


def _stripe_billing_service(request: Request) -> StripeBillingService:
    service = getattr(request.app.state, "stripe_billing_service", None)
    if not isinstance(service, StripeBillingService):
        raise HTTPException(status_code=404, detail="stripe billing is disabled")
    return service


def _settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("application settings are not configured")
    return settings
