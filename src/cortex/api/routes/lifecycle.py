from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cortex.auth.dependencies import require_permission, require_tenant_context
from cortex.config import Settings
from cortex.lifecycle import (
    DeletionTombstone,
    ExportJob,
    InMemoryLifecycleRepository,
    LifecycleDeletionExecutor,
    LifecycleExportExecutor,
    LifecycleRepository,
    LifecycleService,
    SqlAlchemyLifecycleRepository,
)
from cortex.lifecycle.runtime import (
    create_sql_deletion_executor,
    create_sql_export_executor,
)
from cortex.tenancy import TenantContext
from cortex.tenancy.rbac import Permission
from cortex.utils.asyncio import maybe_await

router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])
TENANT_CONTEXT_DEPENDENCY = Depends(require_tenant_context)


class DeletionRequestBody(BaseModel):
    workspace_id: str = Field(min_length=1)
    target_type: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    reason: str = Field(default="customer_request", min_length=1)


class ExportRequestBody(BaseModel):
    workspace_id: str = Field(min_length=1)
    export_scope: str = Field(default="workspace", min_length=1)


class LeaseRequestBody(BaseModel):
    worker_id: str = Field(default="api", min_length=1)
    lease_seconds: int = Field(default=300, ge=30, le=3600)


@router.post("/deletions")
async def request_deletion(
    request: Request,
    body: DeletionRequestBody,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=body.workspace_id,
        permission=Permission.SECURITY_REVIEW,
    )
    async with _lifecycle_repository(request) as (repository, _):
        service = LifecycleService(repository)
        tombstone = await service.request_deletion(
            workspace_id=body.workspace_id,
            target_type=body.target_type,
            target_id=body.target_id,
            requested_by_user_id=context.user_id,
            reason=body.reason,
            queue_execution=True,
        )
    return _tombstone_response(tombstone)


@router.get("/deletions/{workspace_id}/{tombstone_id}")
async def deletion_status(
    request: Request,
    workspace_id: str,
    tombstone_id: str,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SECURITY_REVIEW,
    )
    async with _lifecycle_repository(request) as (repository, _):
        tombstone = await _get_tombstone(repository, tombstone_id, workspace_id)
    return _tombstone_response(tombstone)


@router.post("/deletions/{workspace_id}/{tombstone_id}/lease")
async def lease_deletion(
    request: Request,
    workspace_id: str,
    tombstone_id: str,
    body: LeaseRequestBody,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SECURITY_REVIEW,
    )
    async with _lifecycle_repository(request) as (repository, _):
        await _get_tombstone(repository, tombstone_id, workspace_id)
        tombstone = await maybe_await(
            repository.lease_deletion_tombstone(
                tombstone_id=tombstone_id,
                worker_id=body.worker_id,
                lease_expires_at=datetime.now(UTC)
                + timedelta(seconds=body.lease_seconds),
            )
        )
    return _tombstone_response(tombstone)


@router.post("/deletions/{workspace_id}/{tombstone_id}/execute")
async def execute_deletion(
    request: Request,
    workspace_id: str,
    tombstone_id: str,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SECURITY_REVIEW,
    )
    async with _lifecycle_repository(request) as (repository, session):
        tombstone = await _get_tombstone(repository, tombstone_id, workspace_id)
        target_id = tombstone.metadata_json.get("target_id_ref")
        if not isinstance(target_id, str) or not target_id:
            raise HTTPException(
                status_code=409,
                detail="queued deletion target reference is missing",
            )
        executor = _deletion_executor(request, session)
        service = LifecycleService(repository)
        tombstone = await service.execute_deletion_tombstone(
            tombstone=tombstone,
            target_id=target_id,
            executor=executor,
        )
    return _tombstone_response(tombstone)


@router.post("/deletions/{workspace_id}/{tombstone_id}/retry")
async def retry_deletion(
    request: Request,
    workspace_id: str,
    tombstone_id: str,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SECURITY_REVIEW,
    )
    async with _lifecycle_repository(request) as (repository, _):
        await _get_tombstone(repository, tombstone_id, workspace_id)
        tombstone = await maybe_await(
            repository.retry_deletion_tombstone(
                tombstone_id=tombstone_id,
                error_code="manual_retry",
            )
        )
    return _tombstone_response(tombstone)


@router.post("/exports")
async def request_export(
    request: Request,
    body: ExportRequestBody,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=body.workspace_id,
        permission=Permission.SECURITY_REVIEW,
    )
    async with _lifecycle_repository(request) as (repository, _):
        service = LifecycleService(repository)
        job = await service.request_export(
            workspace_id=body.workspace_id,
            requested_by_user_id=context.user_id,
            export_scope=body.export_scope,
        )
    return _export_response(job)


@router.get("/exports/{workspace_id}/{job_id}")
async def export_status(
    request: Request,
    workspace_id: str,
    job_id: str,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SECURITY_REVIEW,
    )
    async with _lifecycle_repository(request) as (repository, _):
        job = await _get_export_job(repository, job_id, workspace_id)
    return _export_response(job)


@router.post("/exports/{workspace_id}/{job_id}/lease")
async def lease_export(
    request: Request,
    workspace_id: str,
    job_id: str,
    body: LeaseRequestBody,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SECURITY_REVIEW,
    )
    async with _lifecycle_repository(request) as (repository, _):
        await _get_export_job(repository, job_id, workspace_id)
        job = await maybe_await(
            repository.lease_export_job(
                job_id=job_id,
                worker_id=body.worker_id,
                lease_expires_at=datetime.now(UTC)
                + timedelta(seconds=body.lease_seconds),
            )
        )
    return _export_response(job)


@router.post("/exports/{workspace_id}/{job_id}/execute")
async def execute_export(
    request: Request,
    workspace_id: str,
    job_id: str,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SECURITY_REVIEW,
    )
    async with _lifecycle_repository(request) as (repository, session):
        job = await _get_export_job(repository, job_id, workspace_id)
        executor = _export_executor(request, session)
        service = LifecycleService(repository)
        job = await service.execute_export_job(job=job, executor=executor)
    return _export_response(job)


@router.post("/exports/{workspace_id}/{job_id}/retry")
async def retry_export(
    request: Request,
    workspace_id: str,
    job_id: str,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SECURITY_REVIEW,
    )
    async with _lifecycle_repository(request) as (repository, _):
        await _get_export_job(repository, job_id, workspace_id)
        job = await maybe_await(
            repository.retry_export_job(
                job_id=job_id,
                error_code="manual_retry",
            )
        )
    return _export_response(job)


@asynccontextmanager
async def _lifecycle_repository(
    request: Request,
) -> AsyncIterator[tuple[LifecycleRepository, AsyncSession | None]]:
    session_factory = getattr(request.app.state, "session_factory", None)
    if isinstance(session_factory, async_sessionmaker):
        async with session_factory() as session:
            try:
                yield SqlAlchemyLifecycleRepository(session), session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        return
    repository = getattr(request.app.state, "lifecycle_repository", None)
    if repository is None:
        repository = InMemoryLifecycleRepository()
        request.app.state.lifecycle_repository = repository
    yield repository, None


async def _get_tombstone(
    repository: LifecycleRepository,
    tombstone_id: str,
    workspace_id: str,
) -> DeletionTombstone:
    try:
        tombstone = await maybe_await(repository.get_deletion_tombstone(tombstone_id))
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="deletion request not found",
        ) from None
    if tombstone.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="deletion request not found")
    return tombstone


async def _get_export_job(
    repository: LifecycleRepository,
    job_id: str,
    workspace_id: str,
) -> ExportJob:
    try:
        job = await maybe_await(repository.get_export_job(job_id))
    except KeyError:
        raise HTTPException(status_code=404, detail="export job not found") from None
    if job.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="export job not found")
    return job


def _deletion_executor(
    request: Request,
    session: AsyncSession | None,
) -> LifecycleDeletionExecutor:
    if session is not None:
        return create_sql_deletion_executor(
            session=session,
            settings=_settings(request),
        )
    executor = getattr(request.app.state, "lifecycle_deletion_executor", None)
    if executor is None:
        raise HTTPException(
            status_code=503,
            detail="deletion executor is not configured",
        )
    return cast(LifecycleDeletionExecutor, executor)


def _export_executor(
    request: Request,
    session: AsyncSession | None,
) -> LifecycleExportExecutor:
    if session is not None:
        return create_sql_export_executor(session=session, settings=_settings(request))
    executor = getattr(request.app.state, "lifecycle_export_executor", None)
    if executor is None:
        raise HTTPException(status_code=503, detail="export executor is not configured")
    return cast(LifecycleExportExecutor, executor)


def _settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("application settings are not configured")
    return settings


def _tombstone_response(tombstone: DeletionTombstone) -> dict[str, object]:
    return {
        "id": tombstone.id,
        "workspace_id": tombstone.workspace_id,
        "target_type": tombstone.target_type,
        "target_id_hash": tombstone.target_id_hash,
        "status": tombstone.status.value,
        "requested_by_user_id": tombstone.requested_by_user_id,
        "reason": tombstone.reason,
        "created_at": tombstone.created_at.isoformat(),
        "completed_at": (
            tombstone.completed_at.isoformat() if tombstone.completed_at else None
        ),
        "metadata_json": _public_metadata(tombstone.metadata_json),
    }


def _export_response(job: ExportJob) -> dict[str, object]:
    return {
        "id": job.id,
        "workspace_id": job.workspace_id,
        "requested_by_user_id": job.requested_by_user_id,
        "status": job.status.value,
        "export_scope": job.export_scope,
        "destination_ref": job.destination_ref,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "metadata_json": _public_metadata(job.metadata_json),
    }


def _public_metadata(metadata_json: dict[str, object]) -> dict[str, object]:
    redacted: dict[str, object] = {}
    for key, value in metadata_json.items():
        if key in {"target_id_ref"}:
            continue
        redacted[key] = value
    return redacted
