import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";

export default async function EvidencePage({ params }: { params: Promise<{ evidencePackId: string }> }) {
  const { evidencePackId } = await params;
  return <AppShell><main className="mx-auto max-w-4xl p-6"><p className="font-mono text-xs text-muted-foreground">EVIDENCE PACK / {evidencePackId}</p><h1 className="mt-2 text-xl font-semibold">Evidence inspection is local-only.</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">Open this page after a fixture retrieval. The client fetches only the requested pack through the local BFF; it does not expose a broad source browser.</p><EvidenceLoader id={evidencePackId} /><Link className="mt-6 inline-block text-sm text-cortex-blue" href="/ui/context">← Back to context</Link></main></AppShell>;
}

function EvidenceLoader({ id }: { id: string }) { return <div className="cortex-panel mt-6 p-4 text-sm text-muted-foreground">Load this evidence pack from <code>/api/cortex/dev/evidence-packs/{id}</code> after the local fixture service is available.</div>; }
