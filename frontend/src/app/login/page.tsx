import Link from "next/link";
import { ChapterLabel } from "@/components/chapter-label";
import { TrustSignal } from "@/components/product/trust-signal";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-5 py-12 text-foreground">
      <section className="grid w-full max-w-5xl overflow-hidden rounded-lg border border-border bg-popover lg:grid-cols-[0.9fr_1.1fr]">
        <div className="border-b border-border p-6 sm:p-8 lg:border-b-0 lg:border-r">
          <ChapterLabel value="0.1" label="Workspace access" />
          <h1 className="cortex-heading-serif mt-8 text-4xl leading-tight">
            Enter the workspace before asking for context.
          </h1>
          <p className="mt-4 text-sm leading-6 text-muted-foreground">
            Cortex context is scoped to a workspace and checked against source
            permissions before it reaches an agent.
          </p>
          <div className="mt-8 rounded-md border border-warning/30 bg-warning/10 p-4 text-sm leading-6 text-warning-foreground">Local fixture mode has no login or SSO flow. Open the control plane directly to inspect only synthetic fixture data.</div>
          <Link
            className="mt-6 inline-flex text-sm text-muted-foreground hover:text-foreground"
            href="/"
          >
            Back to Cortex
          </Link>
        </div>
        <div className="p-6 sm:p-8">
          <div className="rounded-lg border border-border bg-background p-5">
            <div className="text-xs text-muted-foreground">Access path</div>
            <div className="mt-5 grid gap-3">
              <TrustSignal label="Identity" value="Verified user session" />
              <TrustSignal label="Workspace" value="Active membership context" />
              <TrustSignal label="Sources" value="Slack, GitHub, Linear, docs" />
              <TrustSignal label="Output" value="Cited context bundle" />
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
