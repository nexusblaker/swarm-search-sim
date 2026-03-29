export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="rounded-[28px] border border-dashed border-border/80 bg-surfaceAlt/35 px-6 py-10 text-center">
      <p className="section-kicker">Ready when you are</p>
      <h3 className="mt-2 text-xl font-medium text-white">{title}</h3>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-muted">{body}</p>
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </div>
  );
}
