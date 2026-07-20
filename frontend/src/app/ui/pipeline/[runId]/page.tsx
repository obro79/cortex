import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";

export default async function PipelineRunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  return <AppShell><main className="mx-auto max-w-4xl p-6"><p className="font-mono text-xs text-muted-foreground">PIPELINE RUN / {runId}</p><h1 className="mt-2 text-xl font-semibold">Fixture pipeline run</h1><p className="mt-3 text-sm leading-6 text-muted-foreground">The run record is intentionally scoped to this ID. Poll <code>/api/cortex/dev/pipeline/runs/{runId}</code> once the local fixture runtime is started.</p><Link className="mt-6 inline-block text-sm text-cortex-blue" href="/ui/context">← Back to context</Link></main></AppShell>;
}
