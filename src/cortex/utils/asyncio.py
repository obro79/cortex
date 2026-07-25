from __future__ import annotations

from collections.abc import Awaitable
from inspect import isawaitable
from typing import cast


async def maybe_await[T](value: T | Awaitable[T]) -> T:
    if isawaitable(value):
        return await cast(Awaitable[T], value)
    return value
