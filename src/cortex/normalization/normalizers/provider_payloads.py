from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from cortex.normalization.normalizers.fixtures import FixtureNormalizationError


class ProviderNormalizationError(Exception):
    pass


def load_object(payload_bytes: bytes, provider: str) -> dict[str, Any]:
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError as error:
        raise ProviderNormalizationError(
            f"{provider} payload is not valid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise ProviderNormalizationError(f"{provider} payload must be a JSON object")
    return payload


def required_str(payload: dict[str, Any], key: str, provider: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ProviderNormalizationError(
            f"{provider} payload missing string field: {key}"
        )
    return value


def optional_str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProviderNormalizationError(f"payload field must be a string: {key}")
    return value


def optional_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ProviderNormalizationError(f"payload field must be a list: {key}")
    return value


def parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProviderNormalizationError("datetime field must be an ISO timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ProviderNormalizationError(
            "datetime field must be ISO formatted"
        ) from error


def as_fixture_error(error: ProviderNormalizationError) -> FixtureNormalizationError:
    return FixtureNormalizationError(str(error))
