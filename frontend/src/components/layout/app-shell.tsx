import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/ui/context", label: "Context" },
  { href: "/ui/connectors", label: "Connectors" },
  { href: "/ui/health", label: "Health" },
  { href: "/ui/setup", label: "Setup" },
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
      <header className="border-b border-border">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8 lg:px-12">
          <Link className="text-sm font-semibold" href="/">
            Cortex
          </Link>
          <nav className="hidden items-center gap-5 text-sm text-muted-foreground sm:flex">
            {navItems.map((item) => (
              <Link className="hover:text-foreground" href={item.href} key={item.href}>
                {item.label}
              </Link>
            ))}
          </nav>
          <Link
            className="text-sm font-medium text-muted-foreground hover:text-foreground"
            href="/login"
          >
            Workspace
          </Link>
        </div>
      </header>
      {children}
    </main>
  );
}
