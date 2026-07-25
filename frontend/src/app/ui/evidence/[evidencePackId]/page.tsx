"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { getEvidencePack, type EvidencePackEnvelope } from "@/lib/cortex-api";

export default function EvidencePage({ params }: { params: Promise<{ evidencePackId: string }> }) {
  const [id, setId] = useState<string | null>(null); const [result, setResult] = useState<EvidencePackEnvelope | null>(null); const [error, setError] = useState<string | null>(null);
  useEffect(() => { params.then(({ evidencePackId }) => { setId(evidencePackId); getEvidencePack(evidencePackId).then(setResult).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Evidence pack unavailable.")); }); }, [params]);
  return <AppShell><main className="mx-auto max-w-5xl p-6"><p className="font-mono text-xs text-muted-foreground">EVIDENCE PACK / {id ?? "…"}</p><h1 className="mt-2 text-xl font-semibold">Cited task-context provenance</h1><p className="mt-2 text-sm text-muted-foreground">This route displays the permission-filtered evidence-pack record returned by the backend; it never retrieves providers from the browser or treats the record as a task-context response.</p>{result ? <section className="cortex-panel mt-6 p-4"><dl className="grid gap-3 text-sm sm:grid-cols-2"><div><dt className="text-xs text-muted-foreground">Trace ID</dt><dd className="mt-1 break-all font-mono text-xs">{result.trace_id}</dd></div><div><dt className="text-xs text-muted-foreground">Workspace</dt><dd className="mt-1 break-all font-mono text-xs">{result.workspace_id}</dd></div></dl><pre className="mt-4 overflow-x-auto rounded bg-background p-3 text-xs leading-5 text-muted-foreground">{JSON.stringify(result.evidence_pack, null, 2)}</pre></section> : <div className="cortex-panel mt-6 p-4 text-sm text-muted-foreground">{error ?? "Loading evidence pack…"}</div>}<Link className="mt-6 inline-block text-sm text-cortex-blue" href="/ui/context">← Back to task-context operations</Link></main></AppShell>;
}
