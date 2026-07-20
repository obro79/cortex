"use client";

import Link from "next/link";
import { Copy, ExternalLink, LoaderCircle, Play, Search } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cortexApi } from "@/lib/cortex-api";

type Citation = {
  title?: string;
  source?: string;
  provider?: string;
  citation_url?: string;
  url?: string;
  id?: string;
  chunk_id?: string;
  text?: string;
};

type Retrieval = {
  answer?: string;
  summary?: string;
  context?: string;
  evidence_pack_id?: string;
  citations?: Citation[];
  evidence?: Citation[];
  permission_exclusions?: number;
  freshness?: string;
};

const PREPARED_QUERY = "COR-123 session migration constraints";
const fixtureProviders = ["Slack", "GitHub", "Linear", "Repo docs"];

function valueOf(result: Retrieval) {
  return result.answer ?? result.summary ?? result.context ?? "The fixture API returned no context summary.";
}

export function ContextConsole() {
  const [result, setResult] = useState<Retrieval | null>(null);
  const [message, setMessage] = useState("Seed deterministic fixtures before loading the prepared COR-123 context.");
  const [busy, setBusy] = useState<"seed" | "run" | "query" | null>(null);

  async function action(kind: "seed" | "run" | "query") {
    setBusy(kind);
    setMessage("");
    try {
      if (kind === "seed") {
        await cortexApi("dev/fixtures/seed", { method: "POST" });
        setMessage("Deterministic fixtures seeded. You can run the fixture pipeline or load the prepared COR-123 context.");
      }
      if (kind === "run") {
        const run = await cortexApi<{ run_id?: string }>("dev/pipeline/run", { method: "POST" });
        setMessage(run.run_id ? `Fixture pipeline completed: ${run.run_id}` : "Fixture pipeline completed.");
      }
      if (kind === "query") {
        const next = await cortexApi<Retrieval>("dev/retrieval/query", {
          method: "POST",
          body: JSON.stringify({ query: PREPARED_QUERY }),
        });
        setResult(next);
        setMessage("Prepared COR-123 fixture context loaded. This is not live provider data.");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The local fixture API request failed.");
    } finally {
      setBusy(null);
    }
  }

  const citations = result?.citations ?? result?.evidence ?? [];

  return (
    <div className="mx-auto max-w-[1440px] p-4 sm:p-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3 border-b border-border pb-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground">Fixture context / COR-123</p>
          <h1 className="mt-1 text-xl font-semibold">Review the prepared COR-123 context.</h1>
        </div>
        <Link className="text-sm text-muted-foreground hover:text-foreground" href="/ui/mcp">
          Local MCP setup <ExternalLink className="ml-1 inline size-3" />
        </Link>
      </div>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="cortex-panel overflow-hidden">
          <div className="border-b border-border p-4">
            <p className="text-xs font-medium text-muted-foreground">Prepared, read-only fixture request</p>
            <code className="mt-2 block rounded-md bg-background/70 p-3 text-sm text-foreground">{PREPARED_QUERY}</code>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">This console cannot search freely or query live company data.</p>
            <div className="mt-4 flex justify-end border-t border-border pt-3">
              <Button disabled={busy !== null} onClick={() => action("query")}>
                <Search className="size-4" />
                {busy === "query" ? "Loading fixture context" : "Load prepared context"}
              </Button>
            </div>
          </div>
          <div className="min-h-80 p-4">
            {result ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-sm font-semibold">Cited fixture context bundle</h2>
                  <span className="rounded border border-cortex-green/40 px-2 py-1 font-mono text-[10px] uppercase text-cortex-green">not live data</span>
                </div>
                <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-foreground">{valueOf(result)}</p>
                <div className="mt-6 border-t border-border pt-4">
                  <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Fixture citations</h3>
                  <div className="mt-3 grid gap-2">
                    {citations.length ? citations.map((citation, index) => (
                      <article className="rounded-md border border-border bg-background/50 p-3" key={citation.id ?? citation.chunk_id ?? index}>
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium">{citation.title ?? citation.source ?? citation.provider ?? "Fixture evidence item"}</p>
                            {citation.text && <p className="mt-1 text-xs leading-5 text-muted-foreground">{citation.text}</p>}
                          </div>
                          {(citation.citation_url ?? citation.url) && (
                            <a aria-label={`Open fixture source ${index + 1}`} className="text-cortex-blue" href={citation.citation_url ?? citation.url} rel="noreferrer" target="_blank">
                              <ExternalLink className="size-4" />
                            </a>
                          )}
                        </div>
                      </article>
                    )) : <p className="text-sm text-muted-foreground">This fixture response did not include normalized citation records.</p>}
                  </div>
                </div>
              </>
            ) : (
              <div className="grid min-h-64 place-items-center rounded-md border border-dashed border-border px-6 text-center">
                <div>
                  <p className="text-sm font-medium">No fixture context loaded</p>
                  <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">Seed deterministic fixtures, then load the prepared COR-123 request. No unrestricted search or live provider retrieval is available here.</p>
                </div>
              </div>
            )}
          </div>
        </section>
        <aside className="space-y-4">
          <section className="cortex-panel p-4">
            <h2 className="text-sm font-semibold">Fixture capability gate</h2>
            <p aria-live="polite" className="mt-2 text-sm leading-6 text-muted-foreground">{message}</p>
            <div className="mt-4 grid gap-2">
              <Button disabled={busy !== null} onClick={() => action("seed")} variant="outline">
                {busy === "seed" ? <LoaderCircle className="size-4 animate-spin" /> : null}
                Seed deterministic fixtures
              </Button>
              <Button disabled={busy !== null} onClick={() => action("run")} variant="outline">
                <Play className="size-4" />
                {busy === "run" ? "Running fixture pipeline" : "Run fixture pipeline"}
              </Button>
            </div>
          </section>
          <section className="cortex-panel p-4">
            <h2 className="text-sm font-semibold">Fixture evidence &amp; constraints</h2>
            <dl className="mt-3 grid gap-3 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Fixture coverage (display only)</dt>
                <dd className="mt-1 flex flex-wrap gap-2">{fixtureProviders.map((provider) => <span className="rounded-md border border-border px-2 py-1 text-xs" key={provider}>{provider}</span>)}</dd>
              </div>
              <div><dt className="text-xs text-muted-foreground">Permissions</dt><dd>{result?.permission_exclusions ?? "Reported by the fixture response when available"}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Freshness</dt><dd>{result?.freshness ?? "Fixture timestamps only"}</dd></div>
            </dl>
            {result?.evidence_pack_id && <Link className="mt-4 inline-flex text-sm text-cortex-blue" href={`/ui/evidence/${result.evidence_pack_id}`}>Open fixture evidence pack <ExternalLink className="ml-1 size-3" /></Link>}
            <Button className="mt-4 w-full" disabled={!result} onClick={() => navigator.clipboard.writeText(`${valueOf(result ?? {})}\n\nFixture citations: ${citations.map((item) => item.title ?? item.source ?? "Evidence").join("; ")}`)} variant="outline">
              <Copy className="size-4" />Copy fixture context for agent
            </Button>
          </section>
        </aside>
      </div>
    </div>
  );
}
