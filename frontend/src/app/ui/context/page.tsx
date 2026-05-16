import Link from "next/link";
import { ChapterLabel } from "@/components/chapter-label";
import { SourcePill } from "@/components/product-figure";

export default function ContextConsolePage() {
  return (
    <main className="min-h-screen bg-cortex-bg text-cortex-ink">
      <header className="border-b border-cortex-border px-5 py-5 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link className="text-sm font-semibold" href="/">
            Cortex
          </Link>
          <nav className="flex gap-4 text-sm text-cortex-muted">
            <Link className="hover:text-cortex-ink" href="/ui/context">
              Context
            </Link>
            <Link className="hover:text-cortex-ink" href="/login">
              Workspace
            </Link>
          </nav>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-8 px-5 py-10 sm:px-8 lg:grid-cols-[0.85fr_1.15fr] lg:px-12">
        <div>
          <ChapterLabel value="2.0" label="Context console" />
          <h1 className="mt-6 text-4xl font-semibold leading-tight sm:text-5xl">
            Ask what the agent needs to know.
          </h1>
          <p className="mt-4 text-sm leading-6 text-cortex-muted">
            This is the first authenticated Cortex surface. It turns a task into
            a context bundle with citations, freshness, and permission signals.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <SourcePill name="MCP" tone="green" />
            <SourcePill name="CLI" tone="blue" />
            <SourcePill name="UI" />
          </div>
        </div>

        <section className="rounded-lg border border-cortex-border bg-cortex-panel p-5">
          <label className="text-xs text-cortex-muted" htmlFor="context-query">
            Context request
          </label>
          <textarea
            className="mt-3 min-h-32 w-full resize-none rounded-lg border border-cortex-border bg-cortex-bg p-4 text-sm text-cortex-ink outline-none"
            defaultValue="What should I know before changing billing plan enforcement?"
            id="context-query"
          />
          <div className="mt-4 flex flex-wrap gap-2">
            <SourcePill name="Slack" />
            <SourcePill name="GitHub" />
            <SourcePill name="Linear" />
            <SourcePill name="Repo docs" />
          </div>
          <button className="mt-5 rounded-lg bg-cortex-ink px-4 py-2 text-sm font-semibold text-cortex-bg">
            Get context
          </button>
        </section>
      </section>

      <section className="mx-auto grid max-w-7xl gap-8 px-5 pb-12 sm:px-8 lg:grid-cols-[1.1fr_0.9fr] lg:px-12">
        <div className="rounded-lg border border-cortex-border bg-cortex-panel p-5">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-lg font-semibold">Context bundle</h2>
            <SourcePill name="fresh" tone="green" />
          </div>
          <div className="mt-5 space-y-4">
            <ResultCard
              source="GitHub PR"
              title="SQL-backed billing enforcement"
              detail="Plan checks now use SQL customer, subscription, and usage records."
            />
            <ResultCard
              source="Slack thread"
              title="Launch-gate discussion"
              detail="Backfill and source limits were marked as billing-sensitive."
            />
            <ResultCard
              source="Linear issue"
              title="Production activation"
              detail="Stripe live smoke tests remain a launch-gated evidence item."
            />
          </div>
        </div>

        <aside className="rounded-lg border border-cortex-border bg-cortex-panel p-5">
          <h2 className="text-lg font-semibold">Trust signals</h2>
          <div className="mt-5 space-y-3">
            <Signal label="Evidence pack" value="3 cited objects" />
            <Signal label="Freshness" value="All selected sources current" />
            <Signal label="Permissions" value="1 result excluded" />
            <Signal label="Mode" value="UI preview, MCP-ready" />
          </div>
          <div className="mt-6 grid gap-3">
            <button className="rounded-lg border border-cortex-border px-4 py-2 text-sm font-semibold">
              Copy for agent
            </button>
            <button className="rounded-lg border border-cortex-border px-4 py-2 text-sm font-semibold">
              Open evidence
            </button>
            <button className="rounded-lg border border-cortex-border px-4 py-2 text-sm font-semibold">
              Open source
            </button>
          </div>
        </aside>
      </section>
    </main>
  );
}

function ResultCard({
  source,
  title,
  detail,
}: {
  source: string;
  title: string;
  detail: string;
}) {
  return (
    <article className="rounded-lg border border-cortex-border bg-cortex-bg p-4">
      <div className="text-xs text-cortex-muted">{source}</div>
      <h3 className="mt-2 text-sm font-semibold">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-cortex-muted">{detail}</p>
    </article>
  );
}

function Signal({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-cortex-border pb-3 text-sm last:border-0 last:pb-0">
      <span className="text-cortex-muted">{label}</span>
      <span className="text-right text-cortex-ink">{value}</span>
    </div>
  );
}
