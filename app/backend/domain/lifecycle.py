"""Helpers for summarizing battery lifecycle behavior across runs and reviews."""

from __future__ import annotations

from collections import Counter
from typing import Any


LIFECYCLE_EVENT_ORDER = {
    "approaching_reserve_limit": "approaching reserve limit",
    "critical_battery_margin": "critical battery margin",
    "battery_return_ordered": "return to base ordered",
    "return_to_base": "returned to base",
    "battery_service_started": "battery service started",
    "battery_service_completed": "battery service completed",
    "drone_redeployed": "redeployed",
    "drone_rejoined_search": "back in search",
    "coverage_gap": "coverage gap opened",
    "coverage_rebalanced": "coverage rebalanced",
    "coverage_rebalance_triggered": "coverage rebalance triggered",
}


def summarize_lifecycle_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return a readable lifecycle event summary."""

    event_type = str(event.get("event_type", "event"))
    drone_id = event.get("drone_id")
    title = LIFECYCLE_EVENT_ORDER.get(event_type, event_type.replace("_", " "))
    summary = title.capitalize()
    if drone_id is not None:
        summary = f"Drone {drone_id}: {title}"
    if event_type == "battery_return_ordered":
        summary = f"Drone {drone_id} returned to base to protect reserve margin."
    elif event_type == "battery_service_started":
        summary = f"Drone {drone_id} started recharge or battery swap."
    elif event_type == "battery_service_completed":
        summary = f"Drone {drone_id} completed battery service and became available again."
    elif event_type == "drone_redeployed":
        summary = f"Drone {drone_id} redeployed toward a new mission area."
    elif event_type == "drone_rejoined_search":
        summary = f"Drone {drone_id} rejoined the active search."
    elif event_type == "coverage_gap":
        summary = "Coverage dipped while assets rotated through base."
    elif event_type == "coverage_rebalanced":
        summary = "Coverage stabilized after redeployment."
    return {
        "step": event.get("step"),
        "event_type": event_type,
        "title": title.capitalize(),
        "summary": summary,
    }


def summarize_battery_lifecycle(run_record: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a readable lifecycle summary for reports and reviews."""

    summary_json = run_record.get("summary_json", {})
    metrics = summary_json.get("metrics", {})
    lifecycle_summary = summary_json.get("lifecycle_summary", {})
    lifecycle_events = [event for event in events if str(event.get("event_type")) in LIFECYCLE_EVENT_ORDER]
    event_counts = Counter(str(event.get("event_type")) for event in lifecycle_events)
    highlights = [summarize_lifecycle_event(event) for event in lifecycle_events[:18]]

    returns = int(event_counts.get("battery_return_ordered", 0) or metrics.get("forced_low_battery_returns", 0) or 0)
    recharge_started = int(event_counts.get("battery_service_started", 0) or metrics.get("recharge_cycles_started", 0) or 0)
    recharge_completed = int(event_counts.get("battery_service_completed", 0) or metrics.get("recharge_cycles_completed", 0) or 0)
    redeployments = int(event_counts.get("drone_redeployed", 0) or metrics.get("redeployments", 0) or 0)
    rejoins = int(event_counts.get("drone_rejoined_search", 0) or metrics.get("rejoined_search_events", 0) or 0)
    gap_events = int(event_counts.get("coverage_gap", 0) or metrics.get("coverage_gap_events", 0) or 0)

    minimum_margin = float(metrics.get("battery_margin_min", 0.0) or 0.0)
    average_margin = float(metrics.get("battery_margin_average", 0.0) or 0.0)
    reserve_preset = str(summary_json.get("reserve_preset", lifecycle_summary.get("reserve_preset", "balanced")))
    run_phase = str(summary_json.get("run_phase", lifecycle_summary.get("run_phase", "Active search")))

    continuity_summary = "Coverage stayed mostly stable during asset rotation."
    if gap_events > 0:
        continuity_summary = "Battery rotation created temporary coverage gaps that required rebalance."
    if redeployments > 0 and rejoins > 0:
        continuity_summary += " Redeployed assets successfully restored search presence."

    utilization_summary = (
        f"{returns} return-to-base cycle(s), {recharge_completed} completed service cycle(s), "
        f"and {redeployments} redeployment(s) were recorded."
    )

    if average_margin < 8.0:
        sustainability = "Battery margins stayed tight and the fleet operated close to reserve."
    elif average_margin < 18.0:
        sustainability = "Battery margins were workable but required steady asset rotation."
    else:
        sustainability = "Battery margins remained healthy for sustained coverage."

    return {
        "run_phase": run_phase,
        "reserve_preset": reserve_preset,
        "return_to_base_count": returns,
        "recharge_started_count": recharge_started,
        "recharge_completed_count": recharge_completed,
        "redeploy_count": redeployments,
        "rejoin_count": rejoins,
        "coverage_gap_count": gap_events,
        "battery_margin_summary": {
            "minimum_margin": round(minimum_margin, 2),
            "average_margin": round(average_margin, 2),
            "sustainability": sustainability,
        },
        "asset_utilization_summary": utilization_summary,
        "mission_continuity_impact": continuity_summary,
        "highlights": highlights,
    }

