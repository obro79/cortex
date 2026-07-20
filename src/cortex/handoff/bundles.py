"""Construct safe handoff artifacts without accessing agent sessions."""
from __future__ import annotations

from typing import Any

_RETRIEVAL_RUNTIME = {
    "configured": False,
    "message": "No durable retrieval runtime is configured for this handoff.",
}
_NATIVE_CLAUDE_CAPABILITIES = {
    "resume": {
        "supported": False,
        "reason": "Cortex does not access or resume native Claude sessions.",
    },
    "fork": {
        "supported": False,
        "reason": "Cortex does not access or fork native Claude sessions.",
    },
}


def create_handoff_bundle(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return a portable handoff bundle from explicitly supplied material.

    This deliberately performs no retrieval and never attempts to inspect an
    external agent session. Opaque handles are only copied into the bundle
    after an explicit opt-in by the caller.
    """
    allowed = {
        "approved_summary",
        "evidence_references",
        "opaque_handles",
        "handoff_opt_in",
    }
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        return {"ok": False, "error": "unknown_arguments", "fields": unknown}

    summary = arguments.get("approved_summary")
    if not isinstance(summary, str) or not summary.strip():
        return {
            "ok": False,
            "error": "invalid_arguments",
            "fields": ["approved_summary"],
            "message": "approved_summary must be a non-empty string.",
        }

    evidence = arguments.get("evidence_references", [])
    if not isinstance(evidence, list) or not all(
        isinstance(item, (str, dict)) for item in evidence
    ):
        return {
            "ok": False,
            "error": "invalid_arguments",
            "fields": ["evidence_references"],
            "message": "evidence_references must be a list of strings or objects.",
        }

    handles = arguments.get("opaque_handles", [])
    if not isinstance(handles, list) or not all(
        isinstance(item, str) for item in handles
    ):
        return {
            "ok": False,
            "error": "invalid_arguments",
            "fields": ["opaque_handles"],
            "message": "opaque_handles must be a list of strings.",
        }
    if handles and arguments.get("handoff_opt_in") is not True:
        return {
            "ok": False,
            "error": "handoff_opt_in_required",
            "fields": ["handoff_opt_in"],
            "message": "Set handoff_opt_in to true before including opaque handles.",
        }
    if "handoff_opt_in" in arguments and not isinstance(
        arguments["handoff_opt_in"], bool
    ):
        return {
            "ok": False,
            "error": "invalid_arguments",
            "fields": ["handoff_opt_in"],
            "message": "handoff_opt_in must be a boolean.",
        }

    bundle: dict[str, Any] = {
        "schema_version": "cortex.handoff.v1",
        "approved_summary": summary.strip(),
        "evidence_references": evidence,
        "session_accessed": False,
        "native_claude_resume_supported": False,
        "native_claude_fork_supported": False,
        "retrieval_runtime": _RETRIEVAL_RUNTIME.copy(),
        "native_claude": {
            capability: details.copy()
            for capability, details in _NATIVE_CLAUDE_CAPABILITIES.items()
        },
    }
    if handles:
        bundle["opaque_handles"] = handles
        bundle["handoff_opt_in"] = True

    return {"ok": True, "tool": "create_handoff_bundle", "bundle": bundle}
