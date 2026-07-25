import type { ReactNode } from "react";

type ProductFigureProps = {
  figure: string;
  title: string;
  children: ReactNode;
};

export function ProductFigure({ figure, title, children }: ProductFigureProps) {
  return (
    <figure className="border-y border-border bg-popover/70 px-4 py-5 sm:px-6 lg:px-8">
      <figcaption className="mb-4 flex items-center justify-between gap-4 text-xs text-muted-foreground">
        <span>{figure}</span>
        <span>{title}</span>
      </figcaption>
      {children}
    </figure>
  );
}

export function SourcePill({
  name,
  tone = "default",
}: {
  name: string;
  tone?: "default" | "green" | "amber" | "blue";
}) {
  const tones = {
    default: "border-cortex-border text-cortex-muted",
    green: "border-cortex-green/40 text-cortex-green",
    amber: "border-cortex-amber/50 text-cortex-amber",
    blue: "border-cortex-blue/40 text-cortex-blue",
  };

  return (
    <span className={`rounded-full border px-3 py-1 text-xs ${tones[tone]}`}>
      {name}
    </span>
  );
}
