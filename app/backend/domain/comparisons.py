"""Saved and transient mission plan comparison services."""

from __future__ import annotations

from dataclasses import replace
import time
from typing import Any
from uuid import uuid4

from app.backend.core.settings import BackendSettings
from app.backend.db.sqlite import MetadataStore
from app.backend.domain.assets import apply_asset_package_to_payload
from app.backend.domain.plans import MissionPlanService
from app.backend.domain.reports import ReportService
from app.backend.domain.scenarios import ScenarioService
from app.backend.domain.shared import confidence_band, metrics_to_summary, to_jsonable
from src.simulation.search_patterns import recommend_search_pattern
from src.simulation.engine import SimulationEngine


class ComparisonEvaluator:
    """Evaluate candidate mission plans using short simulation bundles."""

    INTENT_STRATEGIES: dict[str, list[str]] = {
        "broad_area_coverage": ["sector_search", "auction_based", "probability_greedy"],
        "fast_containment": ["auction_based", "information_gain", "sector_search"],
        "high_confidence_confirmation": ["information_gain", "probability_greedy", "auction_based"],
        "battery_conservative": ["sector_search", "probability_greedy", "information_gain"],
    }

    STRATEGY_LABELS = {
        "sector_search": "broad sweep",
        "auction_based": "fast tasking",
        "information_gain": "targeted confirmation",
        "probability_greedy": "focused probability search",
        "random_sweep": "exploratory sweep",
    }

    def __init__(self, scenario_service: ScenarioService, settings: BackendSettings) -> None:
        self.scenario_service = scenario_service
        self.settings = settings

    def compare(self, request: dict[str, Any]) -> dict[str, Any]:
        scenario_payload = self._resolve_payload(request)
        scenario_payload, asset_package = apply_asset_package_to_payload(
            scenario_payload,
            request.get("asset_package") or scenario_payload.get("scenario", {}).get("asset_package"),
        )
        base_config = self.scenario_service.scenario_to_config(scenario_payload)
        mission_intent = str(
            request.get("mission_intent")
            or scenario_payload.get("scenario", {}).get("mission_intent")
            or "broad_area_coverage"
        )
        candidate_requests = self._candidate_requests(request, base_config, asset_package, mission_intent)
        num_seeds = int(request.get("num_seeds", self.settings.comparison_num_seeds))

        ranked_plans: list[dict[str, Any]] = []
        for candidate in candidate_requests:
            metrics = []
            for seed in range(num_seeds):
                config = replace(
                    base_config,
                    strategy=candidate["strategy"],
                    mission_intent=mission_intent,
                    search_pattern=str(candidate.get("search_pattern") or base_config.search_pattern),
                    num_drones=int(candidate["drone_count"]),
                    coordination_mode=str(candidate["coordination_mode"]),
                    return_to_base_threshold=float(candidate["return_threshold"]),
                    seed=base_config.seed + seed,
                    max_steps=min(base_config.max_steps, 30),
                )
                engine = SimulationEngine(config)
                metrics.append(engine.run())
            summary = self._summarize_candidate(
                candidate,
                metrics,
                replace(
                    base_config,
                    strategy=candidate["strategy"],
                    mission_intent=mission_intent,
                    search_pattern=str(candidate.get("search_pattern") or base_config.search_pattern),
                    num_drones=int(candidate["drone_count"]),
                    coordination_mode=str(candidate["coordination_mode"]),
                    return_to_base_threshold=float(candidate["return_threshold"]),
                ),
                asset_package,
                mission_intent,
            )
            ranked_plans.append(summary)

        ranked_plans.sort(key=lambda item: item["score"], reverse=True)
        uncertainty = self._overall_uncertainty(ranked_plans)
        return {
            "ranked_plans": ranked_plans,
            "top_recommendation": ranked_plans[0] if ranked_plans else {},
            "asset_package": asset_package,
            "mission_intent": mission_intent,
            "confidence_summary": {
                "candidate_count": len(ranked_plans),
                "evaluation_seeds": num_seeds,
                "method": "short benchmark bundle",
                "success_band": uncertainty["success_band"],
                "time_band": uncertainty["time_band"],
                "fleet_package": asset_package.get("operator_summary", ""),
                "mission_intent": mission_intent,
            },
            "uncertainty_summary": uncertainty,
            "sensitivity_summary": {
                "strategy_count": len({item["strategy"] for item in ranked_plans}),
                "search_pattern_count": len({item.get("search_pattern") for item in ranked_plans}),
                "drone_count_options": sorted({item["drone_count"] for item in ranked_plans}),
                "coordination_modes": sorted({item["coordination_mode"] for item in ranked_plans}),
                "return_thresholds": sorted({item["return_threshold"] for item in ranked_plans}),
            },
        }

    def _resolve_payload(self, request: dict[str, Any]) -> dict[str, Any]:
        if request.get("scenario_id"):
            return self.scenario_service.load_scenario(str(request["scenario_id"]))["config_json"]
        if request.get("scenario"):
            return request["scenario"]
        if request.get("plan_json"):
            return request["plan_json"]
        raise ValueError("Comparison requires scenario_id, scenario, or plan_json.")

    def _candidate_requests(
        self,
        request: dict[str, Any],
        base_config: Any,
        asset_package: dict[str, Any],
        mission_intent: str,
    ) -> list[dict[str, Any]]:
        fleet = asset_package.get("fleet_composition", {})
        total_drones = int(fleet.get("total_drones") or base_config.num_drones)

        if request.get("candidate_plans"):
            candidates = []
            for index, candidate in enumerate(request["candidate_plans"], start=1):
                candidates.append(
                    {
                        "name": candidate.get("name") or f"Candidate {index}",
                        "strategy": candidate.get("strategy", base_config.strategy),
                        "search_pattern": candidate.get("search_pattern", base_config.search_pattern),
                        "drone_count": int(candidate.get("drone_count", base_config.num_drones)),
                        "coordination_mode": candidate.get("coordination_mode", base_config.coordination_mode),
                        "return_threshold": float(
                            candidate.get("return_threshold", base_config.return_to_base_threshold)
                        ),
                    }
                )
            return candidates

        strategies = request.get("strategies") or self._default_strategies(base_config.strategy, mission_intent, fleet)
        drone_counts = request.get("drone_counts") or self._default_drone_counts(total_drones, mission_intent)
        coordination_modes = request.get("coordination_modes") or self._default_coordination_modes(
            base_config.coordination_mode,
            base_config.scenario_family,
            fleet,
        )
        return_thresholds = request.get("return_thresholds") or self._default_return_thresholds(
            base_config.return_to_base_threshold,
            mission_intent,
            fleet,
        )
        candidates = []
        for strategy in strategies:
            for drone_count in drone_counts:
                for coordination_mode in coordination_modes:
                    for threshold in return_thresholds:
                        candidates.append(
                            {
                                "name": f"{strategy}-{drone_count}d-{coordination_mode}-{threshold}",
                                "strategy": strategy,
                                "search_pattern": request.get("search_pattern") or base_config.search_pattern,
                                "drone_count": int(drone_count),
                                "coordination_mode": str(coordination_mode),
                                "return_threshold": float(threshold),
                            }
                        )
        return candidates[:12]

    def _default_strategies(self, current_strategy: str, mission_intent: str, fleet: dict[str, Any]) -> list[str]:
        preferred = list(self.INTENT_STRATEGIES.get(mission_intent, [current_strategy]))
        if fleet.get("coverage_score", 1.0) >= 1.2 and "sector_search" not in preferred:
            preferred.append("sector_search")
        if fleet.get("detection_score", 1.0) >= 1.15 and "information_gain" not in preferred:
            preferred.append("information_gain")
        if current_strategy not in preferred:
            preferred.append(current_strategy)
        return preferred[:3]

    @staticmethod
    def _default_drone_counts(total_drones: int, mission_intent: str) -> list[int]:
        if total_drones <= 2:
            return [total_drones]
        minimum = max(2, total_drones - 1)
        if mission_intent in {"broad_area_coverage", "fast_containment"}:
            return sorted({minimum, total_drones})
        return [total_drones]

    @staticmethod
    def _default_coordination_modes(
        base_mode: str,
        scenario_family: str,
        fleet: dict[str, Any],
    ) -> list[str]:
        if scenario_family == "poor_comms":
            return ["decentralized"]
        if fleet.get("drone_type_count", 1) > 1 or fleet.get("total_drones", 0) >= 6:
            return ["centralized", "decentralized"]
        return [base_mode]

    @staticmethod
    def _default_return_thresholds(base_threshold: float, mission_intent: str, fleet: dict[str, Any]) -> list[float]:
        endurance = float(fleet.get("aggregate_endurance_minutes") or 120.0)
        baseline = max(22.0, min(36.0, base_threshold))
        if mission_intent == "battery_conservative":
            return [max(baseline, 30.0), max(baseline + 4.0, 34.0)]
        if mission_intent == "fast_containment":
            return [max(22.0, baseline - 4.0), baseline]
        if endurance < 90.0:
            return [max(26.0, baseline), max(30.0, baseline + 2.0)]
        return [baseline]

    @staticmethod
    def _summarize_candidate(
        candidate: dict[str, Any],
        metrics: list[Any],
        candidate_config: Any,
        asset_package: dict[str, Any],
        mission_intent: str,
    ) -> dict[str, Any]:
        success_values = [1.0 if metric.mission_success else 0.0 for metric in metrics]
        detection_times = [
            float(metric.time_to_confirmed_detection or metric.time_to_detection or candidate_config.max_steps)
            for metric in metrics
        ]
        battery_risks = [float(metric.return_to_base_efficiency) for metric in metrics]
        overlaps = [float(metric.overlap_ratio) for metric in metrics]
        comms_failures = [float(metric.comms_failures) for metric in metrics]
        stale_info = [float(metric.stale_information_events) for metric in metrics]
        battery_margin_risk = [max(0.0, 1.0 - float(metric.return_to_base_efficiency)) for metric in metrics]

        success_rate = sum(success_values) / len(metrics)
        expected_detection_time = sum(detection_times) / len(metrics)
        expected_overlap = sum(overlaps) / len(metrics)
        expected_battery_risk = sum(battery_margin_risk) / len(metrics)
        comms_fragility = (sum(comms_failures) + sum(stale_info)) / max(len(metrics), 1)
        heuristics = ComparisonEvaluator._score_with_asset_context(
            candidate,
            asset_package.get("fleet_composition", {}),
            mission_intent,
            candidate_config.scenario_family,
        )
        pattern_decision = recommend_search_pattern(
            candidate_config,
            asset_package.get("fleet_composition", {}),
        )
        score = (
            100.0 * success_rate
            - 0.8 * expected_detection_time
            - 20.0 * expected_overlap
            - 15.0 * expected_battery_risk
            - 1.5 * comms_fragility
            + heuristics["score_adjustment"]
        )
        failure_modes = []
        if expected_battery_risk > 0.45:
            failure_modes.append("battery margin risk")
        if comms_fragility > 4.0:
            failure_modes.append("communications fragility")
        if expected_overlap > 0.18:
            failure_modes.append("overlap inefficiency")
        if success_rate < 0.5:
            failure_modes.append("low mission success")
        if heuristics["battery_watch"]:
            failure_modes.append("fleet endurance is tight for this search")
        if heuristics["coverage_watch"]:
            failure_modes.append("coverage speed may lag the requested search tempo")
        if heuristics["inspection_watch"]:
            failure_modes.append("reduced visibility may create more inspection passes")

        return {
            **candidate,
            "expected_success_rate": round(success_rate, 3),
            "expected_detection_time": round(expected_detection_time, 2),
            "expected_battery_risk": round(expected_battery_risk, 3),
            "expected_overlap": round(expected_overlap, 3),
            "battery_margin_band": confidence_band(battery_margin_risk),
            "success_band": confidence_band(success_values),
            "detection_time_band": confidence_band(detection_times),
            "communications_fragility": round(comms_fragility, 3),
            "overlap_inefficiency": round(expected_overlap, 3),
            "robustness_under_changed_assumptions": "strong" if success_rate >= 0.7 else "moderate" if success_rate >= 0.5 else "fragile",
            "failure_modes": failure_modes or ["no major failure mode flagged"],
            "recommendation_rationale": ComparisonEvaluator._tradeoff_summary(
                success_rate,
                expected_detection_time,
                expected_battery_risk,
                expected_overlap,
                comms_fragility,
            ),
            "operator_fit_summary": heuristics["fit_summary"],
            "key_tradeoffs": heuristics["key_tradeoffs"],
            "sensing_conditions_summary": heuristics["sensing_summary"],
            "inspection_burden": heuristics["inspection_burden"],
            "team_coordination_label": ComparisonEvaluator._coordination_label(candidate["coordination_mode"]),
            **pattern_decision.to_record(),
            "score": round(score, 2),
            "metrics_sample": [metrics_to_summary(metric) for metric in metrics[:3]],
        }

    @staticmethod
    def _score_with_asset_context(
        candidate: dict[str, Any],
        fleet: dict[str, Any],
        mission_intent: str,
        scenario_family: str,
    ) -> dict[str, Any]:
        strategy = str(candidate["strategy"])
        drone_count = int(candidate["drone_count"])
        threshold = float(candidate["return_threshold"])
        coordination_mode = str(candidate["coordination_mode"])
        total_drones = int(fleet.get("total_drones") or drone_count)
        endurance = float(fleet.get("endurance_score") or 1.0)
        coverage = float(fleet.get("coverage_score") or 1.0)
        detection = float(fleet.get("detection_score") or 1.0)
        type_count = int(fleet.get("drone_type_count") or 1)

        score_adjustment = 0.0
        tradeoffs: list[str] = []

        preferred = ComparisonEvaluator.INTENT_STRATEGIES.get(mission_intent, [])
        if preferred:
            if strategy == preferred[0]:
                score_adjustment += 7.0
            elif strategy in preferred[1:]:
                score_adjustment += 3.5
            else:
                score_adjustment -= 2.0

        if mission_intent == "broad_area_coverage":
            score_adjustment += 4.0 if drone_count >= total_drones else 1.0
            if threshold >= 32.0:
                score_adjustment -= 2.0
                tradeoffs.append("keeps more reserve, but slows area coverage")
        elif mission_intent == "fast_containment":
            score_adjustment += 3.0 if threshold <= 28.0 else -1.0
            if threshold <= 26.0:
                tradeoffs.append("pushes batteries harder to move faster")
        elif mission_intent == "high_confidence_confirmation":
            score_adjustment += 3.0 if detection >= 1.08 and strategy in {"information_gain", "probability_greedy"} else -1.0
            if coordination_mode == "centralized":
                score_adjustment += 1.0
            tradeoffs.append("prioritizes confirmation quality over search breadth")
        elif mission_intent == "battery_conservative":
            score_adjustment += 4.0 if threshold >= 30.0 else -2.5
            tradeoffs.append("protects reserve margins but may lengthen search time")

        if coverage >= 1.15 and strategy in {"sector_search", "auction_based"}:
            score_adjustment += 2.5
        if detection >= 1.1 and strategy in {"information_gain", "probability_greedy"}:
            score_adjustment += 2.5
        if endurance < 0.95 and threshold < 28.0:
            score_adjustment -= 3.0
        if type_count > 1 and coordination_mode == "decentralized":
            score_adjustment += 1.5
            tradeoffs.append("mixed fleet reduces idle time when coordination is distributed")
        if scenario_family == "poor_comms" and coordination_mode == "decentralized":
            score_adjustment += 3.0
        if scenario_family == "dense_forest" and strategy == "information_gain":
            score_adjustment += 1.5
            tradeoffs.append("dense cover favors a slower inspect-and-confirm tempo")
        if scenario_family in {"dense_forest", "high_wind", "mixed_terrain"} and mission_intent == "fast_containment":
            tradeoffs.append("faster coverage may still require extra inspect passes before confirmation")

        fit_traits = [
            "strong coverage reach" if coverage >= 1.15 else "moderate coverage reach",
            "good confirmation sensors" if detection >= 1.08 else "standard confirmation sensors",
            "healthy endurance" if endurance >= 1.05 else "tighter endurance",
        ]
        inspection_watch = scenario_family in {"dense_forest", "high_wind"} or detection < 1.0
        if mission_intent == "high_confidence_confirmation":
            inspection_burden = "moderate"
        elif inspection_watch:
            inspection_burden = "elevated"
        else:
            inspection_burden = "light"

        sensing_summary = (
            "Dense cover will likely delay confirmation and create more close inspection passes."
            if scenario_family == "dense_forest"
            else "Reduced visibility may increase the false-positive and inspection burden."
            if scenario_family == "high_wind"
            else "Conditions support a relatively clean cue-to-confirm workflow."
        )
        return {
            "score_adjustment": round(score_adjustment, 2),
            "fit_summary": ", ".join(fit_traits),
            "key_tradeoffs": tradeoffs[:3],
            "battery_watch": endurance < 0.95 and threshold < 28.0,
            "coverage_watch": mission_intent == "broad_area_coverage" and coverage < 1.05,
            "inspection_watch": inspection_watch,
            "inspection_burden": inspection_burden,
            "sensing_summary": sensing_summary,
        }

    @staticmethod
    def _overall_uncertainty(ranked_plans: list[dict[str, Any]]) -> dict[str, Any]:
        success_values = [float(item["expected_success_rate"]) for item in ranked_plans]
        time_values = [float(item["expected_detection_time"]) for item in ranked_plans]
        battery_values = [float(item["expected_battery_risk"]) for item in ranked_plans]
        overlap_values = [float(item["expected_overlap"]) for item in ranked_plans]
        return {
            "success_band": confidence_band(success_values),
            "time_band": confidence_band(time_values),
            "battery_risk_band": confidence_band(battery_values),
            "overlap_band": confidence_band(overlap_values),
        }

    @staticmethod
    def _tradeoff_summary(
        success_rate: float,
        detection_time: float,
        battery_risk: float,
        overlap: float,
        comms_fragility: float,
    ) -> str:
        traits = [
            "higher confidence" if success_rate >= 0.7 else "lower confidence",
            "fast detection" if detection_time <= 15 else "slower detection",
            "battery conservative" if battery_risk <= 0.35 else "battery intensive",
            "low overlap" if overlap <= 0.12 else "higher overlap",
            "comms resilient" if comms_fragility <= 3.0 else "comms fragile",
        ]
        return ", ".join(traits)

    @staticmethod
    def _coordination_label(mode: str) -> str:
        if mode == "decentralized":
            return "distributed team coordination"
        return "guided from a single mission desk"


class PlanComparisonService:
    """Persist saved plan comparison workspaces and their candidate records."""

    def __init__(
        self,
        store: MetadataStore,
        plans: MissionPlanService,
        evaluator: ComparisonEvaluator,
        reports: ReportService | None = None,
    ) -> None:
        self.store = store
        self.plans = plans
        self.evaluator = evaluator
        self.reports = reports

    def list_comparisons(self) -> list[dict[str, Any]]:
        rows = self.store.list("plan_comparisons")
        return sorted(rows, key=lambda item: item["created_at"], reverse=True)

    def get_comparison(self, comparison_id: str) -> dict[str, Any]:
        record = self.store.get("plan_comparisons", comparison_id)
        if record is None:
            raise FileNotFoundError(f"Unknown plan comparison: {comparison_id}")
        record["candidates"] = self.store.list("plan_candidates", "comparison_id = ?", [comparison_id])
        return record

    def create_comparison(self, request: dict[str, Any]) -> dict[str, Any]:
        plan_id = request.get("plan_id")
        plan = self.plans.get_plan(plan_id) if plan_id else None
        evaluation_request = dict(request)
        if plan is not None:
            evaluation_request.setdefault("plan_json", plan["plan_json"])
        result = self.evaluator.compare(evaluation_request)
        comparison_id = f"comparison-{uuid4().hex[:10]}"
        now = time.time()
        name = request.get("name") or (f"{plan['name']} Comparison" if plan else f"comparison-{comparison_id[-4:]}")
        self.store.upsert(
            "plan_comparisons",
            comparison_id,
            {
                "plan_id": plan_id,
                "name": name,
                "status": "completed",
                "created_at": now,
                "updated_at": now,
                "completed_at": now,
                "request_json": to_jsonable(request),
                "summary_json": to_jsonable(result["ranked_plans"]),
                "recommendation_json": to_jsonable(result["top_recommendation"]),
                "uncertainty_json": to_jsonable(result["uncertainty_summary"]),
                "sensitivity_json": to_jsonable(result["sensitivity_summary"]),
                "linked_run_ids_json": [],
                "report_id": None,
                "job_id": None,
            },
        )
        for rank, candidate in enumerate(result["ranked_plans"], start=1):
            candidate_id = f"candidate-{uuid4().hex[:10]}"
            self.store.upsert(
                "plan_candidates",
                candidate_id,
                {
                    "comparison_id": comparison_id,
                    "name": candidate["name"],
                    "rank": rank,
                    "linked_run_id": None,
                    "config_json": to_jsonable(
                        {
                            "strategy": candidate["strategy"],
                            "search_pattern": candidate.get("search_pattern"),
                            "drone_count": candidate["drone_count"],
                            "coordination_mode": candidate["coordination_mode"],
                            "return_threshold": candidate["return_threshold"],
                        }
                    ),
                    "summary_json": to_jsonable(candidate),
                },
            )
        if plan_id:
            self.plans.set_latest_comparison(plan_id, comparison_id)
        comparison_record = self.get_comparison(comparison_id)
        if self.reports is not None:
            report = self.reports.generate_comparison_report(comparison_record)
            self.store.upsert(
                "plan_comparisons",
                comparison_id,
                {
                    "plan_id": comparison_record.get("plan_id"),
                    "name": comparison_record["name"],
                    "status": comparison_record["status"],
                    "created_at": comparison_record["created_at"],
                    "updated_at": time.time(),
                    "completed_at": comparison_record.get("completed_at"),
                    "request_json": comparison_record.get("request_json", {}),
                    "summary_json": comparison_record.get("summary_json", []),
                    "recommendation_json": comparison_record.get("recommendation_json", {}),
                    "uncertainty_json": comparison_record.get("uncertainty_json", {}),
                    "sensitivity_json": comparison_record.get("sensitivity_json", {}),
                    "linked_run_ids_json": comparison_record.get("linked_run_ids_json", []),
                    "report_id": report["id"],
                    "job_id": comparison_record.get("job_id"),
                },
            )
            comparison_record = self.get_comparison(comparison_id)
        return comparison_record

    def get_summary(self, comparison_id: str) -> dict[str, Any]:
        record = self.get_comparison(comparison_id)
        return {
            "comparison_id": comparison_id,
            "summary": record.get("summary_json", []),
            "recommendation_snapshot": record.get("recommendation_json", {}),
            "uncertainty_summary": record.get("uncertainty_json", {}),
            "sensitivity_summary": record.get("sensitivity_json", {}),
        }

    def link_run(self, comparison_id: str, candidate_id: str | None, run_id: str) -> None:
        record = self.get_comparison(comparison_id)
        linked_runs = list(record.get("linked_run_ids_json", []))
        if run_id not in linked_runs:
            linked_runs.append(run_id)
        self.store.upsert(
            "plan_comparisons",
            comparison_id,
            {
                "plan_id": record.get("plan_id"),
                "name": record["name"],
                "status": record["status"],
                "created_at": record["created_at"],
                "updated_at": time.time(),
                "completed_at": record.get("completed_at"),
                "request_json": record.get("request_json", {}),
                "summary_json": record.get("summary_json", []),
                "recommendation_json": record.get("recommendation_json", {}),
                "uncertainty_json": record.get("uncertainty_json", {}),
                "sensitivity_json": record.get("sensitivity_json", {}),
                "linked_run_ids_json": linked_runs,
                "report_id": record.get("report_id"),
                "job_id": record.get("job_id"),
            },
        )
        if candidate_id:
            candidate = self.store.get("plan_candidates", candidate_id)
            if candidate is not None:
                self.store.upsert(
                    "plan_candidates",
                    candidate_id,
                    {
                        "comparison_id": comparison_id,
                        "name": candidate["name"],
                        "rank": candidate["rank"],
                        "linked_run_id": run_id,
                        "config_json": candidate["config_json"],
                        "summary_json": candidate["summary_json"],
                    },
                )
