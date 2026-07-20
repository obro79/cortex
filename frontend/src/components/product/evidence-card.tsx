import { Badge } from "@/components/ui/badge";

export function EvidenceCard({
  detail,
  source,
  title,
}: {
  detail: string;
  source: string;
  title: string;
}) {
  return (
    <article className="rounded-lg border border-border bg-background p-4">
      <Badge variant="outline">{source}</Badge>
      <h3 className="mt-3 text-sm font-semibold text-foreground">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{detail}</p>
    </article>
  );
}
