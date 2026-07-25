import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function SectionShell({
  children,
  className,
  grid = false,
}: {
  children: ReactNode;
  className?: string;
  grid?: boolean;
}) {
  return (
    <section
      className={cn(
        "mx-auto w-full max-w-7xl px-5 py-14 sm:px-8 sm:py-16 lg:px-12",
        grid && "grid gap-10 lg:grid-cols-[0.82fr_1.18fr]",
        className,
      )}
    >
      {children}
    </section>
  );
}
