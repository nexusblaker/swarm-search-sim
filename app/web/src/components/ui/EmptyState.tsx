export function EmptyState({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-3xl border border-dashed border-border bg-surface/60 p-8 text-center">
      <h3 className="text-lg font-medium text-white">{title}</h3>
      <p className="mt-2 text-sm text-muted">{body}</p>
    </div>
  );
}
