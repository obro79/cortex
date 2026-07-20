#!/usr/bin/env python3
"""Exercise the local Cortex MCP stdio protocol without any external services."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _run_server(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    environment = os.environ.copy()
    source_path = str(ROOT / "src")
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{source_path}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else source_path
    )
    process = subprocess.run(
        [sys.executable, "-m", "cortex.mcp.server"],
        cwd=ROOT,
        env=environment,
        input="".join(f"{json.dumps(message)}\n" for message in messages),
        capture_output=True,
        check=False,
        text=True,
    )
    if process.returncode != 0:
        raise RuntimeError(f"MCP server exited {process.returncode}: {process.stderr}")
    return [json.loads(line) for line in process.stdout.splitlines()]


def main() -> None:
    """Verify discovery and the explicit, session-safe handoff opt-in flow."""
    responses = _run_server(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "create_handoff_bundle",
                    "arguments": {
                        "approved_summary": "Demo-approved rollout handoff.",
                        "evidence_references": ["evidence-pack:demo-001"],
                        "opaque_handles": ["opaque:demo-handle"],
                        "handoff_opt_in": True,
                    },
                },
            },
        ]
    )
    if len(responses) != 3:
        raise RuntimeError(f"Expected three JSON-RPC responses, got {len(responses)}")

    tool_names = {tool["name"] for tool in responses[1]["result"]["tools"]}
    bundle = responses[2]["result"]["structuredContent"]["bundle"]
    if "create_handoff_bundle" not in tool_names:
        raise RuntimeError("MCP discovery did not expose create_handoff_bundle")
    if bundle.get("opaque_handles") != ["opaque:demo-handle"]:
        raise RuntimeError("Explicit opaque-handle opt-in was not preserved")
    if bundle.get("session_accessed") is not False:
        raise RuntimeError("Handoff must never access an agent session")
    if bundle.get("native_claude_resume_supported") is not False:
        raise RuntimeError("Handoff must never resume a native Claude session")

    print(
        json.dumps(
            {
                "discovered_tool": "create_handoff_bundle",
                "handoff_opt_in": bundle["handoff_opt_in"],
                "native_claude_resume_supported": bundle[
                    "native_claude_resume_supported"
                ],
                "opaque_handles": bundle["opaque_handles"],
                "session_accessed": bundle["session_accessed"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
