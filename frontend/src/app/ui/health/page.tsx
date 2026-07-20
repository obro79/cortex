"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { getRuntimeHealth, getSourceHealthStatus, type LiveRunCounts, type RuntimeHealth, type SourceHealthStatus } from "@/lib/cortex-api";

const count = (value: number) => value.toLocaleString();
const modes = ["live", "imported_snapshot", "fixture"] as const;

export default function HealthPage() {
  const [health, setHealth] = useState<RuntimeHealth | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [sources, setSources] = useState<SourceHealthStatus | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);
  useEffect(() => { getRuntimeHealth().then(setHealth).catch((reason: unknown) => setHealthError(reason instanceof Error ? reason.message : "Readiness request failed.")); getSourceHealthStatus().then(setSources).catch((reason: unknown) => setSourceError(reason instanceof Error ? reason.message : "Source-health request failed.")); }, []);
  return <AppShell><main className="mx-auto max-w-6xl p-6"><p className="font-mono text-xs text-muted-foreground">SOURCES / HEALTH</p><h1 className="mt-2 text-xl font-semibold">Durable source and retrieval operations</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">This view reads a redacted aggregate projection. It never turns missing credentials or a browser request into a live-data claim.</p>
    <section className="cortex-panel mt-6 p-4"><div className="flex items-center justify-between gap-3"><h2 className="text-sm font-semibold">Local API readiness</h2><span className="font-mono text-xs text-muted-foreground">GET /health/ready</span></div>{health ? <p className="mt-3 text-sm text-muted-foreground">{health.status}{health.issues?.length ? ` · ${health.issues.length} configuration issue(s)` : " · runtime checks available"}</p> : <p className="mt-3 text-sm text-muted-foreground">{healthError ?? "Checking local runtime readiness…"}</p>}</section>
    <section className="cortex-panel mt-4 overflow-hidden"><div className="border-b border-border p-4"><h2 className="text-sm font-semibold">Source health projection</h2><p className="mt-1 text-sm text-muted-foreground">GET /v1/demo-runs/source-health · index and vector counts are shown only when the reporter verifies them.</p></div>{sources?.available ? <SourceTable sources={sources.sources} /> : <p className="p-4 text-sm text-muted-foreground">{sourceError ?? (sources ? "Unavailable: no demo-run source-health projection is configured." : "Loading source health…")}</p>}</section>
    <section className="mt-6 grid gap-3 md:grid-cols-3">{modes.map((mode) => <article className="cortex-panel p-3" key={mode}><p className="font-mono text-xs uppercase text-foreground">{mode}</p><p className="mt-2 text-xs leading-5 text-muted-foreground">{mode === "live" ? "Credentialed data with verified current sync evidence." : mode === "imported_snapshot" ? "Bounded import, explicitly not a live connector." : "Deterministic synthetic data, never provider truth."}</p></article>)}</section>
  </main></AppShell>;
}

function SourceTable({ sources }: { sources: SourceHealthStatus["sources"] }) {
  return <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b border-border text-xs text-muted-foreground"><tr><th className="p-4 font-medium">Source</th><th className="p-4 font-medium">Mode</th><th className="p-4 font-medium">State</th><th className="p-4 font-medium">Events</th><th className="p-4 font-medium">Objects</th><th className="p-4 font-medium">Chunks</th><th className="p-4 font-medium">Embeddings</th><th className="p-4 font-medium">Verified vectors</th></tr></thead><tbody>{sources.map((source) => <tr className="border-b border-border" key={source.source_ref_hash}><td className="p-4 font-mono text-xs">{source.provider}</td><td className="p-4">{source.mode}</td><td className="p-4">{source.readiness} · {source.freshness}</td><Counts cells={source.counts} /></tr>)}</tbody></table></div>;
}

function Counts({ cells }: { cells: LiveRunCounts }) {
  return <><td className="p-4 text-muted-foreground">{count(cells.raw_events)}</td><td className="p-4 text-muted-foreground">{count(cells.source_objects)}</td><td className="p-4 text-muted-foreground">{count(cells.source_chunks)}</td><td className="p-4 text-muted-foreground">{count(cells.embeddings_completed)}</td><td className="p-4 text-muted-foreground">{count(cells.vector_points_verified)}</td></>;
}
