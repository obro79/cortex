"""Narrow local HTTP transport for the MCP task-context tool.

The stdio process is deliberately not an identity provider.  In proxy mode it
uses only a pre-configured local transport identity and never reads workspace,
actor, or session claims from MCP tool arguments.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from cortex.retrieval.task_context import TaskContextRequest, TaskContextResponse

_MAX_HEADERS = 24
_MAX_HEADER_VALUE_BYTES = 2048
_MAX_HEADER_BYTES = 8192
_FORBIDDEN_HEADERS = {
    "connection",
    "content-length",
    "host",
    "transfer-encoding",
}


class McpProxyConfigurationError(ValueError):
    """Raised for a proxy configuration that is unsafe or incomplete."""


@dataclass(frozen=True)
class LocalMcpProxyConfig:
    """Fixed local transport identity used by the opt-in MCP proxy."""

    api_base_url: str
    headers: dict[str, str]
    timeout_seconds: float = 10.0

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> LocalMcpProxyConfig:
        values = environment if environment is not None else os.environ
        api_base_url = values.get("CORTEX_MCP_API_URL", "").strip().rstrip("/")
        if not api_base_url:
            raise McpProxyConfigurationError("CORTEX_MCP_API_URL is required")
        parsed = urlparse(api_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise McpProxyConfigurationError("CORTEX_MCP_API_URL must be an HTTP URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise McpProxyConfigurationError(
                "CORTEX_MCP_API_URL is not a valid API base"
            )

        headers = _headers_from_json(values.get("CORTEX_MCP_HEADERS_JSON", ""))
        timeout_seconds = _timeout_from_environment(
            values.get("CORTEX_MCP_TIMEOUT_SECONDS", "10")
        )
        return cls(
            api_base_url=api_base_url,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )

    @property
    def endpoint_url(self) -> str:
        return f"{self.api_base_url}/v1/context/task-context"


def _headers_from_json(raw: str) -> dict[str, str]:
    if not raw.strip():
        raise McpProxyConfigurationError("CORTEX_MCP_HEADERS_JSON is required")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise McpProxyConfigurationError(
            "CORTEX_MCP_HEADERS_JSON must be a JSON object"
        ) from error
    if not isinstance(parsed, dict) or not parsed:
        raise McpProxyConfigurationError(
            "CORTEX_MCP_HEADERS_JSON must be a non-empty JSON object"
        )
    if len(parsed) > _MAX_HEADERS:
        raise McpProxyConfigurationError("too many configured MCP headers")

    normalized: dict[str, str] = {}
    total_bytes = 0
    for name, value in parsed.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise McpProxyConfigurationError("configured MCP headers must be strings")
        normalized_name = name.strip().lower()
        normalized_value = value.strip()
        if not normalized_name or not normalized_value:
            raise McpProxyConfigurationError("configured MCP headers must not be blank")
        if normalized_name in _FORBIDDEN_HEADERS:
            raise McpProxyConfigurationError("configured MCP header is not allowed")
        if "\r" in normalized_name or "\n" in normalized_name:
            raise McpProxyConfigurationError("configured MCP header is not valid")
        if "\r" in normalized_value or "\n" in normalized_value:
            raise McpProxyConfigurationError("configured MCP header is not valid")
        encoded_size = len(normalized_name.encode()) + len(normalized_value.encode())
        if encoded_size > _MAX_HEADER_VALUE_BYTES:
            raise McpProxyConfigurationError("configured MCP header exceeds size limit")
        total_bytes += encoded_size
        if total_bytes > _MAX_HEADER_BYTES:
            raise McpProxyConfigurationError("configured MCP headers exceed size limit")
        if normalized_name in normalized:
            raise McpProxyConfigurationError("configured MCP headers must be unique")
        normalized[normalized_name] = normalized_value
    return normalized


def _timeout_from_environment(raw: str) -> float:
    try:
        timeout_seconds = float(raw)
    except ValueError as error:
        raise McpProxyConfigurationError(
            "CORTEX_MCP_TIMEOUT_SECONDS must be a number"
        ) from error
    if not 1 <= timeout_seconds <= 30:
        raise McpProxyConfigurationError(
            "CORTEX_MCP_TIMEOUT_SECONDS must be between 1 and 30 seconds"
        )
    return timeout_seconds


@dataclass
class ApiTaskContextProxy:
    """Forward a validated task-context request through a fixed local identity."""

    config: LocalMcpProxyConfig
    transport: httpx.AsyncBaseTransport | None = None

    async def get_task_context(self, request: TaskContextRequest) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    self.config.endpoint_url,
                    headers={**self.config.headers, "content-type": "application/json"},
                    json=request.model_dump(mode="json"),
                )
        except httpx.TimeoutException:
            _diagnostic("task-context request timed out")
            return _proxy_error("MCP_PROXY_TIMEOUT", retryable=True)
        except httpx.HTTPError:
            _diagnostic("task-context request failed")
            return _proxy_error("MCP_PROXY_UNAVAILABLE", retryable=True)

        if response.status_code >= 500:
            _diagnostic(f"task-context API returned {response.status_code}")
            return _proxy_error("MCP_PROXY_UNAVAILABLE", retryable=True)
        if response.status_code >= 400:
            _diagnostic(f"task-context API rejected request ({response.status_code})")
            return _proxy_error("MCP_PROXY_REJECTED", retryable=False)
        try:
            parsed = TaskContextResponse.model_validate(response.json())
        except (ValueError, TypeError):
            _diagnostic("task-context API returned an invalid response")
            return _proxy_error("MCP_PROXY_INVALID_RESPONSE", retryable=True)
        return parsed.model_dump(mode="json", exclude_none=True)


@dataclass(frozen=True)
class UnavailableTaskContextProxy:
    """Fail closed when explicit proxy mode lacks usable configuration."""

    async def get_task_context(self, request: TaskContextRequest) -> dict[str, Any]:
        del request
        return _proxy_error("MCP_PROXY_CONFIGURATION_INVALID", retryable=False)


def _proxy_error(code: str, *, retryable: bool) -> dict[str, Any]:
    messages = {
        "MCP_PROXY_TIMEOUT": "Configured Cortex API did not respond in time.",
        "MCP_PROXY_UNAVAILABLE": "Configured Cortex API is temporarily unavailable.",
        "MCP_PROXY_REJECTED": "Configured Cortex API rejected the request.",
        "MCP_PROXY_INVALID_RESPONSE": (
            "Configured Cortex API returned an invalid response."
        ),
        "MCP_PROXY_CONFIGURATION_INVALID": "Local MCP proxy configuration is invalid.",
    }
    return {
        "ok": False,
        "status": "failed",
        "error": {"code": code, "message": messages[code], "retryable": retryable},
    }


def _diagnostic(message: str) -> None:
    """Keep diagnostics off the JSON-RPC stdout stream and free of secrets."""
    print(f"cortex-mcp: {message}", file=sys.stderr, flush=True)
