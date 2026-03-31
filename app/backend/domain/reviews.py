"""After-action review services."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from app.backend.db.sqlite import MetadataStore
from app.backend.domain.comparisons import PlanComparisonService
from app.backend.domain.lifecycle import (
    summarize_battery_lifecycle,
    summarize_lifecycle_event,
    summarize_sensing_lifecycle,
)
from app.backend.domain.plans import MissionPlanService
from app.backend.domain.reports import ReportService
from app.backend.domain.runs import MissionService


class AfterActionReviewService:
    """Create and retrieve after-action reviews for completed missions."""

    def __init__(
        self,
        store: MetadataStore,
        missions: MissionService,
        plans: MissionPlanService,
        comparisons: PlanComparisonService,
        reports: ReportService,
    ) -> None:
        self.store = store
        self.missions = missions
        self.plans = plans
        self.comparisons = comparisons
        self.reports = reports

    def list_reviews(self) -> list[dict[str, Any]]:
        rows = self.store.list("after_action_reviews")
        return sorted(rows, key=lambda item: item["created_at"], reverse=True)

    def get_review(self, review_id: str) -> dict[str, Any]:
        record = self.store.get("after_action_reviews", review_id)
        if record is None:
            raise FileNotFoundError(f"Unknown after-action review: {review_id}")
        record["report"] = self.reports.get_report(record["report_id"]) if record.get("report_id") else None
        return record

    def create_review(self, request: dict[str, Any]) -> dict[str, Any]:
        run_id = request["run_id"]
        return self.create_from_run(run_id, name=request.get("name"))

    def create_from_run(self, run_id: str, name: str | None = None) -> dict[str, Any]:
        run_record = self.missions.get_run(run_id)
        events = self.missions.get_events(run_id)
        plan_id = run_record.get("plan_id")
        comparison_id = run_record.get("comparison_id")
        plan = self.plans.get_plan(plan_id) if plan_id else None
        comparison = self.comparisons.get_comparison(comparison_id) if comparison_id else None

        timeline = {
            "key_events": [
                {
                    "step": event.get("step"),
                    "event_type": event.get("event_type"),
                    "summary": summarize_lifecycle_event(event).get("summary"),
                    "details": {key: value for key, value in event.items() if key not in {"step", "event_type"}},
                }
                for event in events[:100]
            ],
            "interventions": run_record.get("interventions", []),
            "detection_timeline": [
                event
                for event in events
                if event.get("event_type")
                in {
                    "possible_contact_detected",
                    "inspection_initiated",
                    "inspection_pass_complete",
                    "contact_confirmed",
                    "false_positive_rejected",
                    "search_resumed_after_reject",
                    "confirmed_detection",
                }
            ],
        }
        recommendation = (plan or {}).get("recommendation_json", {})
        top = recommendation.get("top_recommendation") or (comparison or {}).get("recommendation_json", {})
        actual = {
            "strategy": run_record["summary_json"].get("strategy"),
            "num_drones": run_record["summary_json"].get("num_drones"),
            "coordination_mode": run_record["summary_json"].get("coordination_mode"),
            "return_to_base_threshold": run_record["summary_json"].get("return_to_base_threshold"),
        }
        deviation = {
            "strategy_differs": actual["strategy"] != top.get("strategy"),
            "drone_count_differs": actual["num_drones"] != top.get("drone_count"),
            "coordination_differs": actual["coordination_mode"] != top.get("coordination_mode"),
            "reserve_differs": actual["return_to_base_threshold"] != top.get("return_threshold"),
        }
        battery_lifecycle = summarize_battery_lifecycle(run_record, events)
        sensing_lifecycle = summarize_sensing_lifecycle(run_record, events)
        summary = {
            "mission_timeline": (
                f"{sensing_lifecycle['operator_summary']} {battery_lifecycle['mission_continuity_impact']}"
            ),
            "actual_outcome": {
                "status": run_record["status"],
                "metrics": run_record["summary_json"].get("metrics", {}),
            },
            "deviation_from_recommendation": deviation,
            "asset_utilization": {
                "drone_count": actual["num_drones"],
                "battery_used": run_record["summary_json"].get("metrics", {}).get("battery_used"),
                "successful_returns_to_base": run_record["summary_json"].get("metrics", {}).get("successful_returns_to_base"),
                "path_efficiency": run_record["summary_json"].get("metrics", {}).get("path_efficiency"),
            },
            "battery_lifecycle": battery_lifecycle,
            "sensing_lifecycle": sensing_lifecycle,
            "battery_comms_risk_summary": {
                "battery_risk": run_record["summary_json"].get("metrics", {}).get("return_to_base_efficiency"),
                "communications_fragility": run_record["summary_json"].get("metrics", {}).get("comms_failures"),
                "stale_information_events": run_record["summary_json"].get("metrics", {}).get("stale_information_events"),
            },
            "alternate_plan_summary": self._alternate_plan_summary(comparison, actual),
            "links": {
                "run_id": run_id,
                "plan_id": plan_id,
                "comparison_id": comparison_id,
                "replay_path": f"/runs/{run_id}/replay",
                "events_path": f"/runs/{run_id}/events",
            },
        }

        review_id = f"review-{uuid4().hex[:10]}"
        now = time.time()
        review_record = {
            "id": review_id,
            "run_id": run_id,
            "plan_id": plan_id,
            "comparison_id": comparison_id,
            "name": name or f"After Action Review {run_id}",
            "created_at": now,
            "updated_at": now,
            "summary_json": summary,
            "timeline_json": timeline,
            "alternate_plan_json": summary["alternate_plan_summary"],
            "report_id": None,
        }
        report = self.reports.generate_review_report(review_record)
        review_record["report_id"] = report["id"]
        self.store.upsert(
            "after_action_reviews",
            review_id,
            {key: value for key, value in review_record.items() if key != "id"},
        )
        if plan_id:
            self.plans.set_latest_review(plan_id, review_id)
        return self.get_review(review_id)

    @staticmethod
    def _alternate_plan_summary(comparison: dict[str, Any] | None, actual: dict[str, Any]) -> dict[str, Any]:
        if not comparison or not comparison.get("recommendation_json"):
            return {"available": False, "summary": "No saved comparison available for alternate-plan analysis."}
        recommended = comparison["recommendation_json"]
        return {
            "available": True,
            "recommended_strategy": recommended.get("strategy"),
            "recommended_drone_count": recommended.get("drone_count"),
            "actual_strategy": actual["strategy"],
            "actual_drone_count": actual["num_drones"],
            "summary": (
                f"Top saved comparison favored {recommended.get('strategy')} with "
                f"{recommended.get('drone_count')} drones versus actual {actual['strategy']} "
                f"with {actual['num_drones']} drones."
            ),
        }
