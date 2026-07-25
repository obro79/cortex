import Link from "next/link";
import { Activity, Braces, DatabaseZap, HeartPulse, Menu, Search } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { FixtureDisclosure } from "./fixture-disclosure";

const navItems = [
  { href: "/ui/context", label: "Context", icon: Search },
  { href: "/ui/health", label: "Sources / health", icon: HeartPulse },
  { href: "/ui/mcp", label: "MCP setup", icon: Braces },
];

export function AppShell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <main className={cn("min-h-screen bg-background text-foreground", className)}>
      <FixtureDisclosure />
      <div className="min-h-[calc(100vh-35px)] md:grid md:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="hidden border-r border-border bg-popover/40 p-3 md:flex md:flex-col">
          <Link className="flex h-10 items-center gap-2 px-2 text-sm font-semibold" href="/ui/context"><DatabaseZap className="size-4 text-cortex-green" /> Cortex</Link>
          <p className="px-2 pb-3 pt-5 text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">Control plane</p>
          <nav className="grid gap-1" aria-label="Control plane">
            {navItems.map(({ href, label, icon: Icon }) => <Link className="flex h-9 items-center gap-2 rounded-md px-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground" href={href} key={href}><Icon className="size-4" />{label}</Link>)}
          </nav>
          <div className="mt-auto border-t border-border px-2 pt-3 text-xs text-muted-foreground"><Activity className="mr-2 inline size-3 text-cortex-green" />Local development</div>
        </aside>
        <div className="min-w-0">
          <header className="flex h-14 items-center justify-between border-b border-border px-4 sm:px-6">
            <div className="flex items-center gap-2 text-sm md:hidden"><Menu className="size-4" /> Cortex</div>
            <div className="hidden text-xs text-muted-foreground md:block">Workspace / local-dev</div>
            <Link className="text-xs text-muted-foreground hover:text-foreground" href="/">Product overview</Link>
          </header>
          {children}
        </div>
      </div>
    </main>
  );
}
