from typing import Any

TOOL_NAMES = (
    "retrieve_context",
    "get_related_work",
    "check_context_gate",
    "propose_canonical_decision",
    "approve_canonical_decision",
)


def list_tools() -> tuple[str, ...]:
    return TOOL_NAMES


async def call_tool(
    name: str, arguments: dict[str, Any] | None = None
) -> dict[str, Any]:
    if name not in TOOL_NAMES:
        return {"ok": False, "error": "unknown_tool", "tool": name}
    return {
        "ok": False,
        "tool": name,
        "reason": "not_implemented",
        "arguments": arguments or {},
    }
