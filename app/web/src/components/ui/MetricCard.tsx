import { motion } from "framer-motion";

export function MetricCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <motion.div
      layout
      className="rounded-3xl border border-border bg-surfaceAlt/80 p-5 shadow-panel"
      transition={{ duration: 0.2 }}
    >
      <p className="text-xs uppercase tracking-[0.24em] text-muted">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-white">{value}</p>
      {hint && <p className="mt-2 text-sm text-muted">{hint}</p>}
    </motion.div>
  );
}
