import { motion } from "framer-motion";

export function MetricCard({
  label,
  value,
  hint,
  emphasis,
}: {
  label: string;
  value: string | number;
  hint?: string;
  emphasis?: "default" | "accent";
}) {
  return (
    <motion.div
      layout
      className="panel-subtle p-5"
      transition={{ type: "spring", stiffness: 280, damping: 30 }}
    >
      <p className="section-kicker">{label}</p>
      <p className={emphasis === "accent" ? "metric-value mt-3 text-accentStrong" : "metric-value mt-3"}>
        {value}
      </p>
      {hint && <p className="mt-3 text-sm leading-6 text-muted">{hint}</p>}
    </motion.div>
  );
}
