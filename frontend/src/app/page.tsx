import Link from "next/link";
import { ChapterLabel } from "@/components/chapter-label";
import { ProductFigure, SourcePill } from "@/components/product-figure";

const sources = ["Slack", "GitHub", "Linear", "Repo docs"];

export default function Home() {
  return (
    <main className="min-h-screen bg-cortex-bg text-cortex-ink">
      <section className="relative flex min-h-[88vh] flex-col justify-between overflow-hidden border-b border-cortex-border">
        <div className="absolute inset-0">
          <HeroSystemMap />
        </div>
        <header className="relative z-10 flex items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
          <Link className="text-sm font-semibold" href="/">
            Cortex
          </Link>
          <nav className="flex items-center gap-3 text-sm text-cortex-muted">
            <Link className="hover:text-cortex-ink" href="/ui/context">
              Context
            </Link>
            <Link className="hover:text-cortex-ink" href="/login">
              Log in
            </Link>
          </nav>
        </header>
        <div className="relative z-10 max-w-4xl px-5 pb-16 pt-28 sm:px-8 lg:px-12">
          <ChapterLabel value="1.0" label="Cortex" />
          <h1 className="mt-8 max-w-3xl text-5xl font-semibold leading-[1.02] sm:text-6xl lg:text-7xl">
            Give every agent the context it needs to build correctly.
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-7 text-cortex-muted sm:text-lg">
            Cortex lets MCP clients, CLIs, UIs, and coding agents retrieve fresh,
            permission-aware company context from the systems your team already
            uses.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              className="rounded-lg bg-cortex-ink px-4 py-2 text-sm font-semibold text-cortex-bg"
              href="/login"
            >
              Log in
            </Link>
            <Link
              className="rounded-lg border border-cortex-border px-4 py-2 text-sm font-semibold text-cortex-ink"
              href="/ui/context"
            >
              Open context console
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:px-12">
        <div>
          <ChapterLabel value="1.1" label="Ask" />
          <h2 className="mt-5 text-3xl font-semibold sm:text-4xl">
            Ask for the context behind the work.
          </h2>
          <p className="mt-4 text-sm leading-6 text-cortex-muted">
            An engineer or agent should not hunt through every system before
            changing code. Cortex turns the question into a cited context
            request.
          </p>
        </div>
        <ProductFigure figure="FIG. 1.1" title="Context request">
          <div className="rounded-lg border border-cortex-border bg-cortex-bg p-4">
            <div className="text-xs text-cortex-muted">Agent prompt</div>
            <div className="mt-3 text-lg font-medium">
              What should I know before changing billing plan enforcement?
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <SourcePill name="MCP" tone="green" />
              <SourcePill name="CLI" tone="blue" />
              <SourcePill name="UI" />
            </div>
          </div>
        </ProductFigure>
      </section>

      <section className="mx-auto grid max-w-6xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:px-12">
        <div>
          <ChapterLabel value="1.2" label="Retrieve" />
          <h2 className="mt-5 text-3xl font-semibold sm:text-4xl">
            Pull live context from systems teams already use.
          </h2>
          <p className="mt-4 text-sm leading-6 text-cortex-muted">
            Cortex normalizes source truth from conversations, issues, PRs, and
            docs into searchable context for agents.
          </p>
        </div>
        <ProductFigure figure="FIG. 1.2" title="Source retrieval">
          <div className="grid gap-3 md:grid-cols-4">
            {sources.map((source, index) => (
              <div
                className="rounded-lg border border-cortex-border bg-cortex-bg p-4"
                key={source}
              >
                <div className="text-sm font-semibold">{source}</div>
                <div className="mt-4 h-2 rounded bg-cortex-border" />
                <div className="mt-2 h-2 w-2/3 rounded bg-cortex-border" />
                <div className="mt-5 text-xs text-cortex-muted">
                  {index + 2} cited objects
                </div>
              </div>
            ))}
          </div>
        </ProductFigure>
      </section>

      <section className="mx-auto grid max-w-6xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:px-12">
        <div>
          <ChapterLabel value="1.3" label="Verify" />
          <h2 className="mt-5 text-3xl font-semibold sm:text-4xl">
            Every answer comes with source truth.
          </h2>
          <p className="mt-4 text-sm leading-6 text-cortex-muted">
            Results carry citations, freshness, source coverage, and permission
            decisions so the agent can continue with real constraints.
          </p>
        </div>
        <ProductFigure figure="FIG. 1.3" title="Evidence pack">
          <div className="grid gap-4 md:grid-cols-[1.3fr_0.7fr]">
            <div className="rounded-lg border border-cortex-border bg-cortex-bg p-4">
              <div className="text-xs text-cortex-muted">Selected evidence</div>
              <div className="mt-4 space-y-3">
                <EvidenceLine label="Slack thread" value="Plan limits changed after beta review" />
                <EvidenceLine label="GitHub PR" value="SQL-backed billing enforcement" />
                <EvidenceLine label="Linear issue" value="Launch gate follow-up" />
              </div>
            </div>
            <div className="rounded-lg border border-cortex-border bg-cortex-bg p-4">
              <SourcePill name="fresh" tone="green" />
              <div className="mt-3">
                <SourcePill name="permission-aware" tone="blue" />
              </div>
              <div className="mt-3">
                <SourcePill name="1 excluded" tone="amber" />
              </div>
            </div>
          </div>
        </ProductFigure>
      </section>
    </main>
  );
}

function HeroSystemMap() {
  return (
    <div className="h-full w-full opacity-70">
      <div className="mx-auto grid h-full max-w-7xl grid-cols-1 gap-6 px-5 pt-24 sm:px-8 lg:grid-cols-3 lg:px-12">
        <div className="mt-28 hidden rounded-lg border border-cortex-border bg-cortex-panel/80 p-5 lg:block">
          <div className="text-xs text-cortex-muted">Engineer request</div>
          <div className="mt-4 text-sm text-cortex-ink">
            Build plan enforcement without missing context.
          </div>
        </div>
        <div className="mt-16 hidden rounded-lg border border-cortex-green/30 bg-cortex-panel/80 p-5 lg:block">
          <div className="text-xs text-cortex-green">Cortex</div>
          <div className="mt-4 grid gap-2">
            <SourcePill name="MCP" tone="green" />
            <SourcePill name="CLI" tone="blue" />
            <SourcePill name="UI" />
          </div>
        </div>
        <div className="mt-32 hidden rounded-lg border border-cortex-border bg-cortex-panel/80 p-5 lg:block">
          <div className="text-xs text-cortex-muted">Connected sources</div>
          <div className="mt-4 flex flex-wrap gap-2">
            {sources.map((source) => (
              <SourcePill key={source} name={source} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function EvidenceLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-cortex-border pb-3 last:border-0 last:pb-0">
      <div className="text-xs text-cortex-muted">{label}</div>
      <div className="mt-1 text-sm text-cortex-ink">{value}</div>
    </div>
  );
}
