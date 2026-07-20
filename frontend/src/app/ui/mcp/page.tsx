import { AppShell } from "@/components/layout/app-shell";

export default function McpSetupPage() {
  return <AppShell><main className="mx-auto max-w-5xl p-6">
    <p className="font-mono text-xs text-muted-foreground">MCP / SETUP</p><h1 className="mt-2 text-xl font-semibold">Connect an existing agent to cited task context.</h1>
    <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">Cortex supplies evidence through MCP; it does not host a chat workflow or accept browser-supplied workspace authority.</p>
    <div className="mt-6 grid gap-4 lg:grid-cols-2">
      <section className="cortex-panel p-4"><h2 className="text-sm font-semibold">Tool inventory</h2><dl className="mt-4 space-y-3 text-sm"><div><dt className="font-mono text-xs text-cortex-green">get_task_context</dt><dd className="mt-1 text-muted-foreground">Returns permission-filtered cited evidence, coverage, freshness, retrieval status, and a trace ID.</dd></div><div><dt className="font-mono text-xs text-muted-foreground">Compatibility adapters</dt><dd className="mt-1 text-muted-foreground">Existing retrieval tools may remain available, but are not the v1 operator workflow.</dd></div></dl></section>
      <section className="cortex-panel p-4"><h2 className="text-sm font-semibold">Redacted local configuration</h2><pre className="mt-4 overflow-x-auto rounded bg-background p-3 text-xs text-muted-foreground">{`{\n  "mcpServers": {\n    "cortex": {\n      "command": "cortex-mcp",\n      "args": ["serve"],\n      "env": { "CORTEX_*": "[configured locally]" }\n    }\n  }\n}`}</pre><p className="mt-3 text-xs leading-5 text-muted-foreground">Secrets, workspace identifiers, access tokens, and provider configuration are intentionally redacted.</p></section>
      <section className="cortex-panel p-4"><h2 className="text-sm font-semibold">Connection readiness</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">Unavailable — the v1 control-plane API does not yet expose MCP client grants, expiry, or a safe connection-test endpoint.</p><span className="mt-3 inline-block rounded border border-border px-2 py-1 font-mono text-xs">capability gated</span></section>
      <section className="cortex-panel p-4"><h2 className="text-sm font-semibold">Grant revocation</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">Unavailable — revocation controls will appear only after an authenticated grant-management endpoint exists. This placeholder does not claim a connected client or revocable token.</p><span className="mt-3 inline-block rounded border border-border px-2 py-1 font-mono text-xs">capability gated</span></section>
    </div>
  </main></AppShell>;
}
