"use client";

import Link from "next/link";
import { Copy, ExternalLink, LoaderCircle, Play, Search } from "lucide-react";
import { useState } from "react";
import { cortexApi } from "@/lib/cortex-api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type Citation = { title?: string; source?: string; provider?: string; citation_url?: string; url?: string; id?: string; chunk_id?: string; text?: string };
type Retrieval = { answer?: string; summary?: string; context?: string; evidence_pack_id?: string; trace_id?: string; citations?: Citation[]; evidence?: Citation[]; permission_exclusions?: number; freshness?: string };

const providers = ["Slack", "GitHub", "Linear", "Repo docs"];

function valueOf(result: Retrieval) { return result.answer ?? result.summary ?? result.context ?? "The local API returned no context summary."; }

export function ContextConsole() {
  const [query, setQuery] = useState("What should I know before changing billing plan enforcement?");
  const [selected, setSelected] = useState(providers);
  const [result, setResult] = useState<Retrieval | null>(null);
  const [message, setMessage] = useState("Seed fixtures before requesting deterministic context.");
  const [busy, setBusy] = useState<"seed" | "run" | "query" | null>(null);

  async function action(kind: "seed" | "run" | "query") {
    setBusy(kind); setMessage("");
    try {
      if (kind === "seed") { await cortexApi("dev/fixtures/seed", { method: "POST" }); setMessage("Fixtures seeded. You can run the pipeline or request context."); }
      if (kind === "run") { const run = await cortexApi<{ run_id?: string }>("dev/pipeline/run", { method: "POST" }); setMessage(run.run_id ? `Pipeline run started: ${run.run_id}` : "Pipeline run completed."); }
      if (kind === "query") { const next = await cortexApi<Retrieval>("dev/retrieval/query", { method: "POST", body: JSON.stringify({ query }) }); setResult(next); setMessage("Cited context returned by the local fixture service."); }
    } catch (error) { setMessage(error instanceof Error ? error.message : "The local API request failed."); }
    finally { setBusy(null); }
  }

  const citations = result?.citations ?? result?.evidence ?? [];
  return <div className="mx-auto max-w-[1440px] p-4 sm:p-6">
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3 border-b border-border pb-4">
      <div><p className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground">Context / request</p><h1 className="mt-1 text-xl font-semibold">Ask what an agent needs to know.</h1></div>
      <Link className="text-sm text-muted-foreground hover:text-foreground" href="/ui/mcp">Use from MCP <ExternalLink className="ml-1 inline size-3" /></Link>
    </div>
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="cortex-panel overflow-hidden">
        <div className="border-b border-border p-4"><label className="text-xs font-medium text-muted-foreground" htmlFor="context-query">Task-oriented context request</label><Textarea className="mt-2 min-h-28 border-0 bg-transparent px-0 focus-visible:ring-0" id="context-query" onChange={(e) => setQuery(e.target.value)} value={query} />
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3"><div className="flex flex-wrap gap-2" aria-label="Selected fixture providers">{providers.map((provider) => <button aria-pressed={selected.includes(provider)} className={`rounded-md border px-2 py-1 text-xs ${selected.includes(provider) ? "border-cortex-blue/50 bg-cortex-blue/10 text-foreground" : "border-border text-muted-foreground"}`} key={provider} onClick={() => setSelected((current) => current.includes(provider) ? current.filter((item) => item !== provider) : [...current, provider])} type="button">{provider}</button>)}</div><Button disabled={!query.trim() || busy !== null} onClick={() => action("query")}><Search className="size-4" />{busy === "query" ? "Retrieving" : "Get context"}</Button></div>
        </div>
        <div className="min-h-80 p-4">
          {result ? <><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-sm font-semibold">Cited context bundle</h2><span className="rounded border border-cortex-green/40 px-2 py-1 font-mono text-[10px] uppercase text-cortex-green">fixture result</span></div><p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-foreground">{valueOf(result)}</p><div className="mt-6 border-t border-border pt-4"><h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Citations</h3><div className="mt-3 grid gap-2">{citations.length ? citations.map((citation, index) => <article className="rounded-md border border-border bg-background/50 p-3" key={citation.id ?? citation.chunk_id ?? index}><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-medium">{citation.title ?? citation.source ?? citation.provider ?? "Evidence item"}</p>{citation.text && <p className="mt-1 text-xs leading-5 text-muted-foreground">{citation.text}</p>}</div>{(citation.citation_url ?? citation.url) && <a aria-label={`Open source ${index + 1}`} className="text-cortex-blue" href={citation.citation_url ?? citation.url} rel="noreferrer" target="_blank"><ExternalLink className="size-4" /></a>}</div></article>) : <p className="text-sm text-muted-foreground">This response did not include normalized citation records.</p>}</div></div></> : <div className="grid min-h-64 place-items-center rounded-md border border-dashed border-border px-6 text-center"><div><p className="text-sm font-medium">No context bundle yet</p><p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">Seed the deterministic fixtures, then run a focused request. This console does not simulate unrestricted search or live company data.</p></div></div>}
        </div>
      </section>
      <aside className="space-y-4"><section className="cortex-panel p-4"><h2 className="text-sm font-semibold">Fixture capability gate</h2><p aria-live="polite" className="mt-2 text-sm leading-6 text-muted-foreground">{message}</p><div className="mt-4 grid gap-2"><Button disabled={busy !== null} onClick={() => action("seed")} variant="outline">{busy === "seed" ? <LoaderCircle className="size-4 animate-spin" /> : null} Seed deterministic fixtures</Button><Button disabled={busy !== null} onClick={() => action("run")} variant="outline"><Play className="size-4" />{busy === "run" ? "Running pipeline" : "Run fixture pipeline"}</Button></div></section><section className="cortex-panel p-4"><h2 className="text-sm font-semibold">Evidence &amp; constraints</h2><dl className="mt-3 grid gap-3 text-sm"><div><dt className="text-xs text-muted-foreground">Providers selected</dt><dd>{selected.length} fixture source{selected.length === 1 ? "" : "s"}</dd></div><div><dt className="text-xs text-muted-foreground">Permissions</dt><dd>{result?.permission_exclusions ?? "Returned by retrieval when available"}</dd></div><div><dt className="text-xs text-muted-foreground">Freshness</dt><dd>{result?.freshness ?? "Fixture timestamps only"}</dd></div></dl>{result?.evidence_pack_id && <Link className="mt-4 inline-flex text-sm text-cortex-blue" href={`/ui/evidence/${result.evidence_pack_id}`}>Open evidence pack <ExternalLink className="ml-1 size-3" /></Link>}<Button className="mt-4 w-full" disabled={!result} onClick={() => navigator.clipboard.writeText(`${valueOf(result ?? {})}\n\nCitations: ${citations.map((item) => item.title ?? item.source ?? "Evidence").join("; ")}`)} variant="outline"><Copy className="size-4" />Copy for agent</Button></section></aside>
    </div>
  </div>;
}
