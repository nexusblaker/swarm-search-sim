"""Mission plan services for the Phase 7 planning workflow."""

from __future__ import annotations

from copy import deepcopy
import time
from typing import Any, Callable
from uuid import uuid4

import yaml

from app.backend.db.sqlite import MetadataStore
from app.backend.domain.assets import apply_asset_package_to_payload
from app.backend.domain.reports import ReportService
from app.backend.domain.shared import scenario_summary, to_jsonable
from app.backend.domain.scenarios import ScenarioService, TemplateService
from app.backend.storage import LocalProductPaths, slugify


RecommendationFn = Callable[[dict[str, Any]], dict[str, Any]]


class MissionPlanService:
    """Persist and retrieve mission plans built on top of scenarios and templates."""

    def __init__(
        self,
        paths: LocalProductPaths,
        store: MetadataStore,
        scenario_service: ScenarioService,
        template_service: TemplateService,
        recommend: RecommendationFn | None = None,
        reports: ReportService | None = None,
    ) -> None:
        self.paths = paths
        self.store = store
        self.scenario_service = scenario_service
        self.template_service = template_service
        self.recommend = recommend
        self.reports = reports

    def list_plans(self) -> list[dict[str, Any]]:
        rows = self.store.list("mission_plans", "deleted_at IS NULL")
        return sorted(rows, key=lambda item: item["updated_at"], reverse=True)

    def get_plan(self, plan_id: str) -> dict[str, Any]:
        record = self.store.get("mission_plans", plan_id)
        if record is None or record.get("deleted_at") is not None:
            raise FileNotFoundError(f"Unknown mission plan: {plan_id}")
        return record

    def create_plan(self, request: dict[str, Any]) -> dict[str, Any]:
        name = request.get("name") or request.get("plan_name") or f"mission-plan-{uuid4().hex[:8]}"
        plan_id = slugify(request.get("id") or name)
        return self._persist_plan(plan_id, request, existing=self.store.get("mission_plans", plan_id))

    def update_plan(self, plan_id: str, request: dict[str, Any]) -> dict[str, Any]:
        return self._persist_plan(plan_id, request, existing=self.store.get("mission_plans", plan_id))

    def delete_plan(self, plan_id: str) -> None:
        record = self.get_plan(plan_id)
        self.store.upsert(
            "mission_plans",
            plan_id,
            {
                **{key: value for key, value in record.items() if key != "id"},
                "deleted_at": time.time(),
                "updated_at": time.time(),
            },
        )

    def append_linked_run(self, plan_id: str, run_id: str) -> dict[str, Any]:
        record = self.get_plan(plan_id)
        linked = list(record.get("linked_run_ids_json", []))
        if run_id not in linked:
            linked.append(run_id)
        self.store.upsert(
            "mission_plans",
            plan_id,
            {
                "name": record["name"],
                "scenario_id": record.get("scenario_id"),
                "template_id": record.get("template_id"),
                "approval_state": record["approval_state"],
                "created_at": record["created_at"],
                "updated_at": time.time(),
                "deleted_at": record.get("deleted_at"),
                "plan_json": record["plan_json"],
                "summary_json": record["summary_json"],
                "recommendation_json": record.get("recommendation_json", {}),
                "operator_notes": record.get("operator_notes", ""),
                "candidate_alternatives_json": record.get("candidate_alternatives_json", []),
                "priority_zones_json": record.get("priority_zones_json", []),
                "exclusion_zones_json": record.get("exclusion_zones_json", []),
                "latest_comparison_id": record.get("latest_comparison_id"),
                "latest_review_id": record.get("latest_review_id"),
                "linked_run_ids_json": linked,
            },
        )
        return self.get_plan(plan_id)

    def set_latest_comparison(self, plan_id: str, comparison_id: str) -> None:
        record = self.get_plan(plan_id)
        self.store.upsert(
            "mission_plans",
            plan_id,
            {
                "name": record["name"],
                "scenario_id": record.get("scenario_id"),
                "template_id": record.get("template_id"),
                "approval_state": record["approval_state"],
                "created_at": record["created_at"],
                "updated_at": time.time(),
                "deleted_at": record.get("deleted_at"),
                "plan_json": record["plan_json"],
                "summary_json": record["summary_json"],
                "recommendation_json": record.get("recommendation_json", {}),
                "operator_notes": record.get("operator_notes", ""),
                "candidate_alternatives_json": record.get("candidate_alternatives_json", []),
                "priority_zones_json": record.get("priority_zones_json", []),
                "exclusion_zones_json": record.get("exclusion_zones_json", []),
                "latest_comparison_id": comparison_id,
                "latest_review_id": record.get("latest_review_id"),
                "linked_run_ids_json": record.get("linked_run_ids_json", []),
            },
        )

    def set_latest_review(self, plan_id: str, review_id: str) -> None:
        record = self.get_plan(plan_id)
        self.store.upsert(
            "mission_plans",
            plan_id,
            {
                "name": record["name"],
                "scenario_id": record.get("scenario_id"),
                "template_id": record.get("template_id"),
                "approval_state": record["approval_state"],
                "created_at": record["created_at"],
                "updated_at": time.time(),
                "deleted_at": record.get("deleted_at"),
                "plan_json": record["plan_json"],
                "summary_json": record["summary_json"],
                "recommendation_json": record.get("recommendation_json", {}),
                "operator_notes": record.get("operator_notes", ""),
                "candidate_alternatives_json": record.get("candidate_alternatives_json", []),
                "priority_zones_json": record.get("priority_zones_json", []),
                "exclusion_zones_json": record.get("exclusion_zones_json", []),
                "latest_comparison_id": record.get("latest_comparison_id"),
                "latest_review_id": review_id,
                "linked_run_ids_json": record.get("linked_run_ids_json", []),
            },
        )

    def _persist_plan(
        self,
        plan_id: str,
        request: dict[str, Any],
        existing: dict[str, Any] | None,
    ) -> dict[str, Any]:
        resolved = self._resolve_request(request, existing)
        plan_payload = resolved["plan_json"]
        config = self.scenario_service.scenario_to_config(plan_payload)
        recommendation = request.get("recommendation_snapshot")
        if recommendation is None and self.recommend is not None:
            recommendation = self.recommend(
                {
                    "scenario": plan_payload,
                    "asset_package": resolved["asset_package"],
                    "mission_intent": resolved["mission_intent"],
                    "num_seeds": request.get("recommendation_num_seeds", 1),
                }
            )
        plan_path = self.paths.plans_dir / f"{plan_id}.yaml"
        plan_path.write_text(yaml.safe_dump(plan_payload, sort_keys=False), encoding="utf-8")
        now = time.time()
        self.store.upsert(
            "mission_plans",
            plan_id,
            {
                "name": resolved["name"],
                "scenario_id": resolved.get("scenario_id"),
                "template_id": resolved.get("template_id"),
                "approval_state": resolved["approval_state"],
                "created_at": existing["created_at"] if existing else now,
                "updated_at": now,
                "deleted_at": None,
                "plan_json": to_jsonable(plan_payload),
                "summary_json": {
                    **scenario_summary(config),
                    "asset_package": resolved["asset_package"],
                    "reserve_policy": resolved["reserve_policy"],
                    "communication_assumptions": resolved["communication_assumptions"],
                    "map_selection": resolved["map_selection"],
                    "mission_intent": resolved["mission_intent"],
                    "intake_summary": resolved["intake_summary"],
                },
                "recommendation_json": to_jsonable(recommendation or {}),
                "operator_notes": resolved["operator_notes"],
                "candidate_alternatives_json": to_jsonable(resolved["candidate_alternatives"]),
                "priority_zones_json": to_jsonable(resolved["priority_zones"]),
                "exclusion_zones_json": to_jsonable(resolved["exclusion_zones"]),
                "latest_comparison_id": existing.get("latest_comparison_id") if existing else None,
                "latest_review_id": existing.get("latest_review_id") if existing else None,
                "linked_run_ids_json": existing.get("linked_run_ids_json", []) if existing else [],
            },
        )
        plan_record = self.get_plan(plan_id)
        if self.reports is not None:
            self.reports.generate_plan_report(plan_record)
        return plan_record

    def _resolve_request(
        self,
        request: dict[str, Any],
        existing: dict[str, Any] | None,
    ) -> dict[str, Any]:
        existing = existing or {}
        scenario_id = request.get("scenario_id") or existing.get("scenario_id")
        template_id = request.get("template_id") or existing.get("template_id")
        base_payload = request.get("plan_json") or request.get("scenario")
        if base_payload is None:
            if scenario_id:
                base_payload = deepcopy(self.scenario_service.load_scenario(str(scenario_id))["config_json"])
            elif template_id:
                base_payload = deepcopy(self.template_service.get_template(str(template_id))["config_json"])
            elif existing.get("plan_json"):
                base_payload = deepcopy(existing["plan_json"])
            else:
                raise ValueError("MissionPlan requires scenario_id, template_id, scenario, or plan_json.")
        else:
            base_payload = deepcopy(base_payload)

        scenario_block = base_payload.setdefault("scenario", {})
        asset_package = dict(request.get("asset_package") or existing.get("summary_json", {}).get("asset_package", {}))
        reserve_policy = dict(request.get("reserve_policy") or existing.get("summary_json", {}).get("reserve_policy", {}))
        communication_assumptions = dict(
            request.get("communication_assumptions")
            or existing.get("summary_json", {}).get("communication_assumptions", {})
        )
        map_selection = dict(request.get("map_selection") or existing.get("summary_json", {}).get("map_selection", {}))
        intake_summary = dict(request.get("intake_summary") or existing.get("summary_json", {}).get("intake_summary", {}))
        mission_intent = request.get("mission_intent") or existing.get("summary_json", {}).get("mission_intent")

        if request.get("strategy"):
            scenario_block["strategy"] = request["strategy"]
        if request.get("search_pattern"):
            scenario_block["search_pattern"] = request["search_pattern"]
        if request.get("num_drones") is not None:
            scenario_block["num_drones"] = int(request["num_drones"])
        if request.get("weather"):
            scenario_block["weather"] = request["weather"]
        if request.get("target_behavior"):
            scenario_block.setdefault("target_assumptions", {})["behavior"] = request["target_behavior"]

        if reserve_policy:
            scenario_block.setdefault("battery_policy", {}).update(reserve_policy)
        if communication_assumptions:
            scenario_block.setdefault("communication", {}).update(communication_assumptions)
        if map_selection:
            scenario_block["mission_area"] = map_selection
            for key in ("use_external_layers", "layer_paths", "scenario_family"):
                if key in map_selection:
                    scenario_block[key] = map_selection[key]

        if request.get("name"):
            scenario_block["name"] = request["name"]
        if mission_intent:
            scenario_block["mission_intent"] = mission_intent

        if asset_package:
            base_payload, asset_package = apply_asset_package_to_payload(base_payload, asset_package)
            scenario_block = base_payload.setdefault("scenario", {})

        return {
            "name": request.get("name") or existing.get("name") or scenario_block.get("name", plan_id_from_payload(base_payload)),
            "scenario_id": scenario_id,
            "template_id": template_id,
            "approval_state": request.get("approval_state") or existing.get("approval_state", "draft"),
            "plan_json": base_payload,
            "operator_notes": request.get("operator_notes") or existing.get("operator_notes", ""),
            "candidate_alternatives": request.get("candidate_alternatives") or existing.get("candidate_alternatives_json", []),
            "priority_zones": request.get("priority_zones") or existing.get("priority_zones_json", []),
            "exclusion_zones": request.get("exclusion_zones") or existing.get("exclusion_zones_json", []),
            "asset_package": asset_package or scenario_block.get("drone", {}),
            "reserve_policy": reserve_policy or scenario_block.get("battery_policy", {}),
            "communication_assumptions": communication_assumptions or scenario_block.get("communication", {}),
            "mission_intent": mission_intent,
            "intake_summary": intake_summary,
            "map_selection": map_selection
            or {
                "use_external_layers": scenario_block.get("use_external_layers", False),
                "layer_paths": scenario_block.get("layer_paths", {}),
                "scenario_family": scenario_block.get("scenario_family", "mixed_terrain"),
            },
        }


def plan_id_from_payload(payload: dict[str, Any]) -> str:
    """Return a stable plan-ish name from the plan payload."""

    return payload.get("scenario", {}).get("name", "mission-plan")
