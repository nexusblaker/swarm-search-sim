import { cn } from "@/lib/cn";

export function RiskIndicator({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "warning" | "good" | "danger";
}) {
  const toneClass =
    tone === "warning"
      ? "border-warning/30 bg-warning/10 text-[#e6d7bc]"
      : tone === "good"
        ? "border-success/30 bg-success/10 text-[#dce7e0]"
        : tone === "danger"
          ? "border-danger/30 bg-danger/10 text-[#ecd6d9]"
          : "border-border bg-surfaceAlt/65 text-white";

  return (
    <div className={cn("rounded-[22px] border px-4 py-4", toneClass)}>
      <p className="section-kicker">{label}</p>
      <p className="mt-2 text-base font-medium">{value}</p>
    </div>
  );
}
