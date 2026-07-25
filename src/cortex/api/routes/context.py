from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from cortex.auth.dependencies import require_tenant_context, resolve_provider_principals
from cortex.observability.tracing import ensure_trace_context
from cortex.runtime import CortexAuthority, CortexRuntime
from cortex.tenancy import TenantContext

router = APIRouter(prefix="/v1/context", tags=["context"])
TenantDependency = Annotated[TenantContext, Depends(require_tenant_context)]


class ContextQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=20_000)
    source_allowlist: list[str] = Field(default_factory=list)
    provider_filters: list[str] = Field(default_factory=list)


class ContextGateQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str | None = Field(default=None, min_length=1, max_length=20_000)
    evidence_pack_id: str | None = None
    task_hints: dict[str, object] = Field(default_factory=dict)
    source_allowlist: list[str] = Field(default_factory=list)
    provider_filters: list[str] = Field(default_factory=list)


class ContextResponse(BaseModel):
    contract_version: Literal["v1"] = "v1"
    trace_id: str
    workspace_id: str
    retrieval_request_id: str
    evidence_pack_id: str | None
    status: str
    latency_ms: int | None
    text: str
    evidence_pack: dict[str, object]


class GateResponse(BaseModel):
    contract_version: Literal["v1"] = "v1"
    trace_id: str
    workspace_id: str
    context_gate_result_id: str | None
    status: str
    text: str
    result: dict[str, object]


def _runtime(request: Request) -> CortexRuntime:
    runtime = getattr(request.app.state, "cortex_runtime", None)
    if not isinstance(runtime, CortexRuntime):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "context_runtime_unavailable",
                "message": "context retrieval is not configured",
            },
        )
    return runtime


async def _authority(request: Request, context: TenantContext) -> CortexAuthority:
    principals = await resolve_provider_principals(request, context)
    trace = ensure_trace_context(
        trace_id=context.trace_id, workspace_id=context.workspace_id
    )
    return CortexAuthority(
        workspace_id=context.workspace_id,
        actor_id=context.user_id,
        trace_id=trace.trace_id,
        caller_principals=tuple(principals),
    )


@router.post("/query", response_model=ContextResponse)
async def query_context(
    request: Request, body: ContextQuery, context: TenantDependency
) -> ContextResponse:
    authority = await _authority(request, context)
    response = await _runtime(request).retrieve(
        authority=authority,
        query=body.query,
        source_allowlist=body.source_allowlist,
        provider_filters=body.provider_filters,
    )
    return ContextResponse(
        trace_id=authority.trace_id,
        workspace_id=authority.workspace_id,
        retrieval_request_id=response.retrieval_request_id,
        evidence_pack_id=response.evidence_pack_id,
        status=response.status,
        latency_ms=response.latency_ms,
        text=response.text,
        evidence_pack=response.evidence_pack,
    )


@router.post("/gate", response_model=GateResponse)
async def check_context_gate(
    request: Request, body: ContextGateQuery, context: TenantDependency
) -> GateResponse:
    authority = await _authority(request, context)
    response = await _runtime(request).check_gate(
        authority=authority,
        query=body.query,
        evidence_pack_id=body.evidence_pack_id,
        task_hints=body.task_hints,
        source_allowlist=body.source_allowlist,
        provider_filters=body.provider_filters,
    )
    if response is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "context_gate_unavailable",
                "message": "context gate is not configured",
            },
        )
    return GateResponse(
        trace_id=authority.trace_id,
        workspace_id=authority.workspace_id,
        context_gate_result_id=response.context_gate_result_id,
        status=response.status,
        text=response.text,
        result=response.result,
    )


@router.get("/evidence/{evidence_pack_id}")
async def evidence_bootstrap(
    request: Request, evidence_pack_id: str, context: TenantDependency
) -> dict[str, object]:
    authority = await _authority(request, context)
    evidence_pack = _runtime(request).evidence_bootstrap(
        authority=authority, evidence_pack_id=evidence_pack_id
    )
    if evidence_pack is None:
        raise HTTPException(status_code=404, detail="evidence pack not found")
    return {
        "contract_version": "v1",
        "trace_id": authority.trace_id,
        "workspace_id": authority.workspace_id,
        "evidence_pack": evidence_pack,
    }


@router.get("/status")
async def context_status(
    request: Request, context: TenantDependency
) -> dict[str, object]:
    authority = await _authority(request, context)
    runtime = _runtime(request)
    return {
        "contract_version": "v1",
        "trace_id": authority.trace_id,
        "workspace_id": authority.workspace_id,
        "available": True,
        "live_data": runtime.live_data,
        "context_gate_available": runtime.context_gate is not None,
    }
