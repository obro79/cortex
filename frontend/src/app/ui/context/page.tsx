import { Copy, ExternalLink, Search } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { SectionShell } from "@/components/layout/section-shell";
import { ChapterLabel } from "@/components/chapter-label";
import { EvidenceCard } from "@/components/product/evidence-card";
import { SourcePill } from "@/components/product/source-pill";
import { TrustSignal } from "@/components/product/trust-signal";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export default function ContextConsolePage() {
  return (
    <AppShell>
      <SectionShell className="grid gap-8 py-10 lg:grid-cols-[0.85fr_1.15fr]">
        <div>
          <ChapterLabel value="2.0" label="Context console" />
          <h1 className="cortex-heading-serif mt-6 max-w-xl text-4xl leading-tight sm:text-5xl">
            Ask what the agent needs to know.
          </h1>
          <p className="mt-4 max-w-lg text-sm leading-6 text-muted-foreground">
            This is the first authenticated Cortex surface. It turns a task into
            a context bundle with citations, freshness, and permission signals.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <SourcePill name="MCP" tone="green" />
            <SourcePill name="CLI" tone="blue" />
            <SourcePill name="UI" />
          </div>
        </div>

        <section className="cortex-panel p-5">
          <label className="text-xs text-muted-foreground" htmlFor="context-query">
            Context request
          </label>
          <Textarea
            className="mt-3 min-h-32 resize-none"
            defaultValue="What should I know before changing billing plan enforcement?"
            id="context-query"
          />
          <div className="mt-4 flex flex-wrap gap-2">
            <SourcePill name="Slack" />
            <SourcePill name="GitHub" />
            <SourcePill name="Linear" />
            <SourcePill name="Repo docs" />
          </div>
          <Button className="mt-5">
            <Search aria-hidden="true" />
            Get context
          </Button>
        </section>
      </SectionShell>

      <SectionShell className="grid gap-8 pb-12 pt-0 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="cortex-panel p-5">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-lg font-semibold">Context bundle</h2>
            <SourcePill name="fresh" tone="green" />
          </div>
          <div className="mt-5 space-y-4">
            <EvidenceCard
              source="GitHub PR"
              title="SQL-backed billing enforcement"
              detail="Plan checks now use SQL customer, subscription, and usage records."
            />
            <EvidenceCard
              source="Slack thread"
              title="Launch-gate discussion"
              detail="Backfill and source limits were marked as billing-sensitive."
            />
            <EvidenceCard
              source="Linear issue"
              title="Production activation"
              detail="Stripe live smoke tests remain a launch-gated evidence item."
            />
          </div>
        </div>

        <aside className="cortex-panel p-5">
          <h2 className="text-lg font-semibold">Trust signals</h2>
          <div className="mt-5 space-y-3">
            <TrustSignal label="Evidence pack" value="3 cited objects" />
            <TrustSignal label="Freshness" value="All selected sources current" />
            <TrustSignal label="Permissions" value="1 result excluded" />
            <TrustSignal label="Mode" value="UI preview, MCP-ready" />
          </div>
          <div className="mt-6 grid gap-3">
            <Button variant="outline">
              <Copy aria-hidden="true" />
              Copy for agent
            </Button>
            <Button variant="outline">
              <ExternalLink aria-hidden="true" />
              Open evidence
            </Button>
            <Button variant="outline">
              <ExternalLink aria-hidden="true" />
              Open source
            </Button>
          </div>
        </aside>
      </SectionShell>
    </AppShell>
  );
}
