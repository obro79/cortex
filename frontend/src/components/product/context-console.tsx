"use client";

import Link from "next/link";
import { LoaderCircle, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { getDemoRunReport, requestTaskContext, type DemoRunReportStatus, type TaskContextResponse } from "@/lib/cortex-api";

const DIAGNOSTIC_REQUEST = {
  task: { objective: "Control-plane diagnostic: verify that cited task context is available." },
  budget: { maximum_evidence_items: 5, maximum_tokens: 1200 },
} as const;

export function ContextConsole() {
  const [result, setResult] = useState<TaskContextResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reportStatus, setReportStatus] = useState<DemoRunReportStatus | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  useEffect(() => { getDemoRunReport().then(setReportStatus).catch((reason: unknown) => setReportError(reason instanceof Error ? reason.message : "Demo report unavailable.")); }, []);
  async function runDiagnostic() {
    setBusy(true); setError(null);
    try { setResult(await requestTaskContext(DIAGNOSTIC_REQUEST)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Task-context diagnostic failed."); }
    finally { setBusy(false); }
  }
  return <main className="mx-auto max-w-6xl p-6">
    <p className="font-mono text-xs text-muted-foreground">TASK CONTEXT / OPERATIONS</p><h1 className="mt-2 text-xl font-semibold">Inspect evidence returned by the MCP contract.</h1>
    <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">This is a fixed, read-only diagnostic request—not a chat composer or a free-form company search.</p>
    <section className="cortex-panel mt-6 p-4"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-sm font-medium">Task-context readiness check</p><code className="mt-2 block text-xs text-muted-foreground">cortex.task_context.v1</code></div><Button disabled={busy} onClick={runDiagnostic}>{busy ? <LoaderCircle className="size-4 animate-spin" /> : <Play className="size-4" />}{busy ? "Checking" : "Run diagnostic"}</Button></div></section>
    <section className="cortex-panel mt-4 p-4"><div className="flex items-center justify-between gap-3"><h2 className="text-sm font-semibold">Demo flight recorder</h2><span className="font-mono text-xs text-muted-foreground">GET /v1/demo-runs/latest</span></div>{reportStatus?.available && reportStatus.report ? <p className="mt-3 text-sm text-muted-foreground">{reportStatus.report.outcome} · {reportStatus.report.live_data ? "live" : "fixture or imported"} · {reportStatus.report.counts.query_requests} recorded {reportStatus.report.counts.query_requests === 1 ? "query" : "queries"}. Persisted report contains aggregate counts and opaque hashes only.</p> : <p className="mt-3 text-sm text-muted-foreground">{reportError ?? (reportStatus ? "Unavailable: no demo-run projection is configured." : "Loading aggregate run status…")}</p>}</section>
    {error && <section className="mt-4 rounded-lg border border-red-400/30 bg-red-400/10 p-4 text-sm"><p className="font-medium">Unavailable</p><p className="mt-1 text-muted-foreground">{error}</p></section>}
    {result && <section className="cortex-panel mt-4 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-sm font-semibold">Contract result</h2><span className="rounded border border-border px-2 py-1 font-mono text-xs">{result.status}</span></div>{result.ok && result.task_context ? <><dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4"><div><dt className="text-xs text-muted-foreground">Data mode</dt><dd className="mt-1">{result.live_data ? "live" : "fixture or imported snapshot"}</dd></div><div><dt className="text-xs text-muted-foreground">Evidence</dt><dd className="mt-1">{result.task_context.source_coverage.evidence_item_count}</dd></div><div><dt className="text-xs text-muted-foreground">Freshness</dt><dd className="mt-1">{result.task_context.freshness.status}</dd></div><div><dt className="text-xs text-muted-foreground">Retrieval</dt><dd className="mt-1">{result.task_context.retrieval.status}</dd></div></dl><div className="mt-4 border-t border-border pt-4 text-sm"><p className="text-xs text-muted-foreground">Trace ID</p><code>{result.trace_id}</code>{result.evidence_pack_id && <Link className="ml-4 text-cortex-blue" href={`/ui/evidence/${result.evidence_pack_id}`}>Inspect evidence pack →</Link>}</div></> : result.ok ? <p className="mt-3 text-sm text-muted-foreground">The response did not include a task-context record. Trace {result.trace_id}</p> : <><p className="mt-3 text-sm text-muted-foreground">{result.error.message}</p><p className="mt-2 font-mono text-xs text-muted-foreground">{result.error.code} · trace {result.trace_id}</p></>}</section>}
  </main>;
}
