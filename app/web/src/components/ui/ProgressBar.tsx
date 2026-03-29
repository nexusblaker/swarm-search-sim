export function ProgressBar({ value = 0 }: { value?: number }) {
  const width = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className="h-2.5 overflow-hidden rounded-full bg-surfaceAlt">
      <div
        className="h-full rounded-full bg-gradient-to-r from-accent to-emerald-400 transition-all duration-300"
        style={{ width: `${width}%` }}
      />
    </div>
  );
}
