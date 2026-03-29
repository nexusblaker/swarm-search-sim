export function DetailPanel({
  title,
  items,
}: {
  title: string;
  items: Array<{ label: string; value: React.ReactNode }>;
}) {
  return (
    <div className="panel-subtle p-5">
      <p className="section-kicker">{title}</p>
      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div key={item.label} className="flex flex-col gap-1 border-b border-border/60 pb-3 last:border-b-0 last:pb-0">
            <span className="text-xs uppercase tracking-[0.14em] text-muted">{item.label}</span>
            <div className="text-sm leading-6 text-white">{item.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
