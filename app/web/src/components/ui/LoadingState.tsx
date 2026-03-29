export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="rounded-3xl border border-border bg-surface/85 p-8 text-center text-sm text-muted shadow-panel">
      {label}
    </div>
  );
}
