import { RiskIndicator } from "@/components/ui/RiskIndicator";

export function ComparisonSummaryCard({
  title,
  description,
  metrics,
}: {
  title: string;
  description: string;
  metrics: Array<{ label: string; value: string; tone?: "neutral" | "warning" | "good" | "danger" }>;
}) {
  return (
    <div className="panel-subtle p-5">
      <p className="section-kicker">Analysis summary</p>
      <h3 className="mt-2 text-lg font-semibold text-white">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {metrics.map((metric) => (
          <RiskIndicator key={metric.label} label={metric.label} value={metric.value} tone={metric.tone} />
        ))}
      </div>
    </div>
  );
}
