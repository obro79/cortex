from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from cortex.platform.cache import CacheUnavailableError, EphemeralCacheService
from cortex.platform.rate_limits import (
    RateLimitDecision,
    RateLimitPolicy,
    RateLimitService,
    RateLimitSubject,
)

HEALTH_PATH_PREFIX = "/health/"


def install_api_rate_limit(
    app: FastAPI, *, cache: EphemeralCacheService, policy: RateLimitPolicy
) -> None:
    service = RateLimitService(cache)

    @app.middleware("http")
    async def api_rate_limit(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path.startswith(HEALTH_PATH_PREFIX):
            return await call_next(request)

        try:
            decision = service.check(policy, _subject_from_request(request))
        except CacheUnavailableError:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "rate limit service unavailable",
                    "code": "rate_limit_unavailable",
                },
            )

        if not decision.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "rate limit exceeded",
                    "code": "rate_limit_exceeded",
                    "retry_after_seconds": decision.retry_after_seconds,
                },
                headers=_headers(decision),
            )

        response = await call_next(request)
        response.headers.update(_headers(decision))
        return response


def _subject_from_request(request: Request) -> RateLimitSubject:
    client = request.client.host if request.client is not None else "unknown-client"
    return RateLimitSubject(
        workspace_id=request.headers.get("x-workspace-id", "anonymous-workspace"),
        user_id=request.headers.get("x-user-id", "anonymous-user"),
        client_id=client,
    )


def _headers(decision: RateLimitDecision) -> dict[str, str]:
    retry_after = decision.retry_after_seconds
    headers = {
        "X-RateLimit-Limit": str(decision.limit),
        "X-RateLimit-Remaining": str(decision.remaining),
    }
    if retry_after:
        headers["Retry-After"] = str(retry_after)
    return headers
