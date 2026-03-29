export function ProgressBar({ value = 0 }: { value?: number }) {
  const normalized = value <= 1 ? value * 100 : value;
  const width = Math.max(0, Math.min(100, Math.round(normalized)));
  return (
    <div
      className="h-2.5 overflow-hidden rounded-full bg-white/[0.06]"
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={width}
    >
      <div
        data-testid="progress-fill"
        className="h-full rounded-full bg-gradient-to-r from-accentStrong via-accent to-success transition-all duration-500"
        style={{ width: `${width}%` }}
      />
    </div>
  );
}
