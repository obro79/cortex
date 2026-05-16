import Link from "next/link";
import { ChapterLabel } from "@/components/chapter-label";
import { SourcePill } from "@/components/product-figure";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-cortex-bg px-5 py-12 text-cortex-ink">
      <section className="grid w-full max-w-5xl overflow-hidden rounded-lg border border-cortex-border bg-cortex-panel lg:grid-cols-[0.9fr_1.1fr]">
        <div className="border-b border-cortex-border p-6 sm:p-8 lg:border-b-0 lg:border-r">
          <ChapterLabel value="0.1" label="Workspace access" />
          <h1 className="mt-8 text-4xl font-semibold leading-tight">
            Enter the workspace before asking for context.
          </h1>
          <p className="mt-4 text-sm leading-6 text-cortex-muted">
            Cortex context is scoped to a workspace and checked against source
            permissions before it reaches an agent.
          </p>
          <div className="mt-8 space-y-3">
            <button className="w-full rounded-lg bg-cortex-ink px-4 py-3 text-sm font-semibold text-cortex-bg">
              Continue with email
            </button>
            <button className="w-full rounded-lg border border-cortex-border px-4 py-3 text-sm font-semibold text-cortex-ink">
              Continue with SSO
            </button>
          </div>
          <Link
            className="mt-6 inline-flex text-sm text-cortex-muted hover:text-cortex-ink"
            href="/"
          >
            Back to Cortex
          </Link>
        </div>
        <div className="p-6 sm:p-8">
          <div className="rounded-lg border border-cortex-border bg-cortex-bg p-5">
            <div className="text-xs text-cortex-muted">Access path</div>
            <div className="mt-5 grid gap-3">
              <AccessRow label="Identity" value="Verified user session" />
              <AccessRow label="Workspace" value="Active membership context" />
              <AccessRow label="Sources" value="Slack, GitHub, Linear, docs" />
              <AccessRow label="Output" value="Cited context bundle" />
            </div>
            <div className="mt-6 flex flex-wrap gap-2">
              <SourcePill name="workspace-scoped" tone="green" />
              <SourcePill name="permission-aware" tone="blue" />
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function AccessRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-cortex-border pb-3 text-sm last:border-0 last:pb-0">
      <span className="text-cortex-muted">{label}</span>
      <span className="text-right font-medium text-cortex-ink">{value}</span>
    </div>
  );
}
