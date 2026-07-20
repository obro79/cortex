type ChapterLabelProps = {
  value: string;
  label: string;
};

export function ChapterLabel({ value, label }: ChapterLabelProps) {
  return (
    <div className="flex items-center gap-3 text-xs font-medium text-cortex-muted">
      <span className="rounded-full border border-cortex-border px-3 py-1 text-cortex-ink">
        {value}
      </span>
      <span>{label}</span>
    </div>
  );
}
