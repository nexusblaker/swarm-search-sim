import type {
  BatteryLifecycleSummary,
  LifecycleSummaryRecord,
  SnapshotDrone,
} from "@/api/types";

const LIFECYCLE_STATE_LABELS: Record<string, string> = {
  deploying: "Deploying",
  searching: "Searching",
  returning_to_base: "Returning to Base",
  recharging_or_swapping: "Recharging",
  ready_to_redeploy: "Ready to Redeploy",
  redeploying: "Redeploying",
  unavailable: "Unavailable",
};

const RESERVE_LABELS: Record<string, string> = {
  safe: "Safe",
  approaching_reserve_limit: "Approaching Reserve",
  returning_now: "Returning Now",
  critical_battery_margin: "Critical Margin",
};

const EVENT_LABELS: Record<string, string> = {
  approaching_reserve_limit: "Approaching Reserve",
  critical_battery_margin: "Critical Battery Margin",
  battery_return_ordered: "Return to Base Ordered",
  return_to_base: "Returned to Base",
  battery_service_started: "Battery Service Started",
  battery_service_completed: "Battery Service Completed",
  drone_redeployed: "Redeployed",
  drone_rejoined_search: "Back in Search",
  coverage_gap: "Coverage Gap",
  coverage_rebalanced: "Coverage Rebalanced",
  coverage_rebalance_triggered: "Coverage Rebalance Triggered",
};

export function lifecycleStateLabel(state?: string | null): string {
  if (!state) return "Unknown";
  return LIFECYCLE_STATE_LABELS[state] ?? startCase(state);
}

export function reserveStatusLabel(status?: string | null): string {
  if (!status) return "Reserve Stable";
  return RESERVE_LABELS[status] ?? startCase(status);
}

export function startCase(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function formatBatteryPercent(value?: number | null): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "n/a";
  }
  return `${Math.round(value)}%`;
}

export function batteryBarClass(value?: number | null): string {
  if (typeof value !== "number") {
    return "bg-slate-500";
  }
  if (value <= 15) return "bg-rose-400";
  if (value <= 35) return "bg-amber-300";
  return "bg-emerald-400";
}

export function formatStepEta(value?: number | null, readyLabel = "Ready now"): string {
  if (value === null || value === undefined) {
    return "ETA unavailable";
  }
  if (value <= 0) {
    return readyLabel;
  }
  return `${value} step${value === 1 ? "" : "s"}`;
}

export function serviceEtaLabel(drone: SnapshotDrone): string {
  if (drone.lifecycle_state === "recharging_or_swapping") {
    return `Ready in ${formatStepEta(drone.turnaround_remaining_steps, "Ready now")}`;
  }
  if (drone.lifecycle_state === "returning_to_base") {
    return `Back in service in ${formatStepEta(drone.return_service_eta_steps, "Ready now")}`;
  }
  if (drone.lifecycle_state === "ready_to_redeploy") {
    return "Ready now";
  }
  if (drone.lifecycle_state === "redeploying") {
    return "Rejoining coverage";
  }
  return "In mission";
}

export function eventPresentation(event: Record<string, unknown>): {
  title: string;
  summary: string;
  details: Record<string, unknown>;
} {
  const eventType = String(event.event_type ?? event.action ?? "event");
  const title = EVENT_LABELS[eventType] ?? startCase(eventType);
  const summary =
    typeof event.summary === "string"
      ? event.summary
      : typeof event.reason === "string"
        ? event.reason
        : title;
  const details = Object.fromEntries(
    Object.entries(event).filter(([key]) => !["summary"].includes(key)),
  );
  return { title, summary, details };
}

export function isLifecycleEvent(event: Record<string, unknown>): boolean {
  const eventType = String(event.event_type ?? event.action ?? "");
  return eventType in EVENT_LABELS;
}

export function asLifecycleSummary(summary?: LifecycleSummaryRecord | null): LifecycleSummaryRecord {
  return summary ?? {};
}

export function asBatteryLifecycle(summary?: BatteryLifecycleSummary | null): BatteryLifecycleSummary {
  return summary ?? {};
}
