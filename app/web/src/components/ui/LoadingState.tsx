export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="panel-surface flex items-center gap-4 p-6 text-sm text-muted">
      <div className="h-10 w-10 animate-pulse rounded-2xl bg-surfaceAlt/90" />
      <div className="space-y-2">
        <p className="text-sm font-medium text-white">{label}</p>
        <p className="text-xs uppercase tracking-[0.16em] text-muted">Preparing workspace</p>
      </div>
    </div>
  );
}
