"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { getRuntimeHealth, type RuntimeHealth } from "@/lib/cortex-api";

type SourceMode = "live" | "imported snapshot" | "fixture" | "syncing" | "stale" | "failed" | "unavailable";
const modes: Array<{ mode: SourceMode; description: string }> = [
  { mode: "live", description: "Credentialed source has current durable sync evidence." },
  { mode: "imported snapshot", description: "Bounded offline import; not a live connector." },
  { mode: "fixture", description: "Deterministic synthetic data; never provider truth." },
  { mode: "syncing", description: "A durable sync is in progress; counts may lag." },
  { mode: "stale", description: "Last known data exceeds its requested freshness window." },
  { mode: "failed", description: "A sync/runtime path failed; do not infer healthy data." },
  { mode: "unavailable", description: "No health projection endpoint is enabled yet." },
];

export default function HealthPage() {
  const [health, setHealth] = useState<RuntimeHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getRuntimeHealth().then(setHealth).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Readiness request failed.")); }, []);

  return <AppShell><main className="mx-auto max-w-6xl p-6">
    <p className="font-mono text-xs text-muted-foreground">SOURCES / HEALTH</p>
    <h1 className="mt-2 text-xl font-semibold">Durable source and retrieval operations</h1>
    <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">Counts only become operational truth when a source-health projection is available. This UI will not infer source health from a browser request.</p>
    <section className="cortex-panel mt-6 p-4">
      <div className="flex items-center justify-between gap-3"><h2 className="text-sm font-semibold">Local API readiness</h2><span className="font-mono text-xs text-muted-foreground">GET /health/ready</span></div>
      {health ? <div className="mt-3 text-sm"><span className="rounded border border-border px-2 py-1 font-mono text-xs">{health.status}</span>{health.issues?.length ? <ul className="mt-3 space-y-2 text-muted-foreground">{health.issues.map((issue) => <li key={`${issue.field}-${issue.code}`}>{issue.field}: {issue.message}</li>)}</ul> : <p className="mt-3 text-muted-foreground">Runtime configuration checks are available; connector and index counts remain capability-gated.</p>}</div> : <p className="mt-3 text-sm text-muted-foreground">{error ?? "Checking local runtime readiness…"}</p>}
    </section>
    <section className="cortex-panel mt-4 overflow-hidden">
      <div className="border-b border-border p-4"><h2 className="text-sm font-semibold">Source health projection</h2><p className="mt-1 text-sm text-muted-foreground">No JSON source-health/count endpoint is in the v1 task-context contract yet.</p></div>
      <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b border-border text-xs text-muted-foreground"><tr><th className="p-4 font-medium">Source</th><th className="p-4 font-medium">State</th><th className="p-4 font-medium">Events</th><th className="p-4 font-medium">Objects</th><th className="p-4 font-medium">Chunks</th><th className="p-4 font-medium">Embeddings</th><th className="p-4 font-medium">Index points</th></tr></thead><tbody><tr><td className="p-4">No source projection</td><td className="p-4"><span className="rounded border border-border px-2 py-1 font-mono text-xs">unavailable</span></td><td className="p-4 text-muted-foreground">—</td><td className="p-4 text-muted-foreground">—</td><td className="p-4 text-muted-foreground">—</td><td className="p-4 text-muted-foreground">—</td><td className="p-4 text-muted-foreground">—</td></tr></tbody></table></div>
    </section>
    <section className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">{modes.map(({ mode, description }) => <article className="cortex-panel p-3" key={mode}><p className="font-mono text-xs uppercase text-foreground">{mode}</p><p className="mt-2 text-xs leading-5 text-muted-foreground">{description}</p></article>)}</section>
  </main></AppShell>;
}
