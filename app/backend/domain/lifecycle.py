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
    "possible_contact_detected": "possible contact detected",
    "inspection_initiated": "inspection initiated",
    "inspection_pass_complete": "inspection pass complete",
    "contact_confirmed": "contact confirmed",
    "false_positive_rejected": "false alarm rejected",
    "search_resumed_after_reject": "search resumed",
}

SENSING_EVENT_TYPES = {
    "possible_contact_detected",
    "inspection_initiated",
    "inspection_pass_complete",
    "contact_confirmed",
    "false_positive_rejected",
    "search_resumed_after_reject",
    "confirmed_detection",
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
    elif event_type == "possible_contact_detected":
        summary = f"Drone {drone_id} flagged a possible contact that requires inspection."
    elif event_type == "inspection_initiated":
        summary = f"Drone {drone_id} moved to inspect the possible contact."
    elif event_type == "inspection_pass_complete":
        outcome = str(event.get("outcome", "pending"))
        if outcome == "confirmed":
            summary = f"Drone {drone_id} completed an inspection pass and confirmed the contact."
        elif outcome == "rejected":
            summary = f"Drone {drone_id} completed an inspection pass and rejected the contact."
        else:
            summary = f"Drone {drone_id} completed an inspection pass but the contact remains uncertain."
    elif event_type == "contact_confirmed":
        summary = f"Drone {drone_id} confirmed the target after close inspection."
    elif event_type == "false_positive_rejected":
        summary = f"Drone {drone_id} rejected the contact as a false alarm."
    elif event_type == "search_resumed_after_reject":
        summary = f"Drone {drone_id} resumed the wider search after rejecting the contact."
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


def summarize_sensing_lifecycle(run_record: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a readable cue -> inspect -> confirm summary for reports and reviews."""

    summary_json = run_record.get("summary_json", {})
    metrics = summary_json.get("metrics", {})
    sensing_summary = summary_json.get("sensing_summary", {})
    sensing_events = [event for event in events if str(event.get("event_type")) in SENSING_EVENT_TYPES]
    event_counts = Counter(str(event.get("event_type")) for event in sensing_events)
    highlights = [summarize_lifecycle_event(event) for event in sensing_events[:18]]

    candidate_count = int(
        metrics.get("candidate_detection_count", 0)
        or event_counts.get("possible_contact_detected", 0)
        or 0
    )
    inspections_started = int(
        metrics.get("inspections_initiated", 0)
        or event_counts.get("inspection_initiated", 0)
        or 0
    )
    inspection_passes = int(
        metrics.get("inspections_completed", 0)
        or event_counts.get("inspection_pass_complete", 0)
        or 0
    )
    confirmed = int(
        metrics.get("confirmed_contact_count", 0)
        or event_counts.get("contact_confirmed", 0)
        or event_counts.get("confirmed_detection", 0)
        or 0
    )
    rejected = int(
        metrics.get("rejected_contact_count", 0)
        or event_counts.get("false_positive_rejected", 0)
        or 0
    )

    active_candidates = int(sensing_summary.get("active_candidate_contacts", 0) or 0)
    under_inspection = int(sensing_summary.get("contacts_under_inspection", 0) or 0)
    pending = int(sensing_summary.get("confirmation_pending", 0) or 0)

    operator_summary = "No cue or inspection activity was recorded."
    if confirmed > 0:
        operator_summary = "The mission progressed from a possible contact to a confirmed target after inspection."
    elif candidate_count > 0 and rejected > 0:
        operator_summary = "The team investigated possible contacts and rejected false alarms before resuming the search."
    elif candidate_count > 0:
        operator_summary = "Possible contacts were detected and tracked for closer inspection."

    inspection_burden = "Inspection burden remained light."
    if inspections_started >= 3 or inspection_passes >= 4:
        inspection_burden = "The team spent meaningful mission time on repeated inspection passes."
    elif inspections_started > 0:
        inspection_burden = "A limited number of inspection passes were needed to resolve possible contacts."

    mission_impact = "Broad search remained the dominant mission activity."
    if confirmed > 0:
        mission_impact = "Confirmation activity focused the mission on a credible target contact."
    elif rejected > 0:
        mission_impact = "False alarms briefly pulled assets into inspection before the search resumed."

    return {
        "candidate_detection_count": candidate_count,
        "inspection_initiated_count": inspections_started,
        "inspection_pass_count": inspection_passes,
        "confirmed_detection_count": confirmed,
        "false_positive_count": rejected,
        "active_candidate_contacts": active_candidates,
        "contacts_under_inspection": under_inspection,
        "confirmation_pending": pending,
        "operator_summary": operator_summary,
        "inspection_burden_summary": inspection_burden,
        "mission_impact_summary": mission_impact,
        "highlights": highlights,
    }
