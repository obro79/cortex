import { Badge } from "@/components/ui/badge";

const toneToVariant = {
  amber: "warning",
  blue: "info",
  green: "success",
  neutral: "secondary",
} as const;

export function SourcePill({
  name,
  tone = "neutral",
}: {
  name: string;
  tone?: keyof typeof toneToVariant;
}) {
  return <Badge variant={toneToVariant[tone]}>{name}</Badge>;
}
