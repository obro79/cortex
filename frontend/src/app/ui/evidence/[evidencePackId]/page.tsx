"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { EvidenceInspector } from "@/components/product/evidence-inspector";
import { cortexApi, type TaskContextSuccess } from "@/lib/cortex-api";

export default function EvidencePage({ params }: { params: Promise<{ evidencePackId: string }> }) {
  const [id, setId] = useState<string | null>(null); const [result, setResult] = useState<TaskContextSuccess | null>(null); const [error, setError] = useState<string | null>(null);
  useEffect(() => { params.then(({ evidencePackId }) => { setId(evidencePackId); cortexApi<TaskContextSuccess>(`v1/task-context/evidence/${evidencePackId}`).then(setResult).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Evidence pack unavailable.")); }); }, [params]);
  return <AppShell><main className="mx-auto max-w-5xl p-6"><p className="font-mono text-xs text-muted-foreground">EVIDENCE PACK / {id ?? "…"}</p><h1 className="mt-2 text-xl font-semibold">Cited task-context provenance</h1><p className="mt-2 text-sm text-muted-foreground">Evidence is rendered from the same permission-filtered task-context DTO; it is never retrieved from providers in the browser.</p>{result ? <div className="mt-6"><EvidenceInspector context={result.task_context} traceId={result.trace_id} /></div> : <div className="cortex-panel mt-6 p-4 text-sm text-muted-foreground">{error ?? "Loading evidence pack…"}</div>}<Link className="mt-6 inline-block text-sm text-cortex-blue" href="/ui/context">← Back to task-context operations</Link></main></AppShell>;
}
