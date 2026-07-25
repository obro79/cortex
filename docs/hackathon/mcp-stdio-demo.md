# MCP stdio demo

Run the deterministic local demo with:

```bash
python scripts/mcp_protocol_smoke.py
```

The script starts `cortex.mcp.server` as a subprocess and sends newline-delimited
JSON-RPC through stdin. It verifies `tools/list` discovery and creates a handoff
only from an explicitly supplied, approved summary. The demo opts in to copying an
opaque handle, but it never reads, resumes, or forks a Claude session; its output
asserts those capabilities remain unavailable.

This is a local demo transport only. Production use still needs authenticated
transport, caller authorization, tenancy isolation, rate limits, audit logging,
and operational monitoring.
