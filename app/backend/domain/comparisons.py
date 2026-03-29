"""Saved and transient mission plan comparison services."""

from __future__ import annotations

from dataclasses import replace
import time
from typing import Any
from uuid import uuid4

from app.backend.core.settings import BackendSettings
from app.backend.db.sqlite import MetadataStore
from app.backend.domain.plans import MissionPlanService
from app.backend.domain.reports import ReportService
from app.backend.domain.scenarios import ScenarioService
from app.backend.domain.shared import confidence_band, metrics_to_summary, scenario_summary, to_jsonable
from src.simulation.engine import SimulationEngine


class ComparisonEvaluator:
    """Evaluate candidate mission plans using short simulation bundles."""

    def __init__(self, scenario_service: ScenarioService, settings: BackendSettings) -> None:
        self.scenario_service = scenario_service
        self.settings = settings

    def compare(self, request: dict[str, Any]) -> dict[str, Any]:
        scenario_payload = self._resolve_payload(request)
        base_config = self.scenario_service.scenario_to_config(scenario_payload)
        candidate_requests = self._candidate_requests(request, base_config)
        num_seeds = int(request.get("num_seeds", self.settings.comparison_num_seeds))

        ranked_plans: list[dict[str, Any]] = []
        for candidate in candidate_requests:
            metrics = []
            for seed in range(num_seeds):
                config = replace(
                    base_config,
                    strategy=candidate["strategy"],
                    num_drones=int(candidate["drone_count"]),
                    coordination_mode=str(candidate["coordination_mode"]),
                    return_to_base_threshold=float(candidate["return_threshold"]),
                    seed=base_config.seed + seed,
                    max_steps=min(base_config.max_steps, 30),
                )
                engine = SimulationEngine(config)
                metrics.append(engine.run())
            summary = self._summarize_candidate(candidate, metrics, base_config.max_steps)
            ranked_plans.append(summary)

        ranked_plans.sort(key=lambda item: item["score"], reverse=True)
        uncertainty = self._overall_uncertainty(ranked_plans)
        return {
            "ranked_plans": ranked_plans,
            "top_recommendation": ranked_plans[0] if ranked_plans else {},
            "confidence_summary": {
                "candidate_count": len(ranked_plans),
                "evaluation_seeds": num_seeds,
                "method": "short benchmark bundle",
                "success_band": uncertainty["success_band"],
                "time_band": uncertainty["time_band"],
            },
            "uncertainty_summary": uncertainty,
            "sensitivity_summary": {
                "strategy_count": len({item["strategy"] for item in ranked_plans}),
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

    @staticmethod
    def _candidate_requests(request: dict[str, Any], base_config: Any) -> list[dict[str, Any]]:
        if request.get("candidate_plans"):
            candidates = []
            for index, candidate in enumerate(request["candidate_plans"], start=1):
                candidates.append(
                    {
                        "name": candidate.get("name") or f"Candidate {index}",
                        "strategy": candidate.get("strategy", base_config.strategy),
                        "drone_count": int(candidate.get("drone_count", base_config.num_drones)),
                        "coordination_mode": candidate.get("coordination_mode", base_config.coordination_mode),
                        "return_threshold": float(
                            candidate.get("return_threshold", base_config.return_to_base_threshold)
                        ),
                    }
                )
            return candidates

        strategies = request.get("strategies") or [base_config.strategy]
        drone_counts = request.get("drone_counts") or [base_config.num_drones]
        coordination_modes = request.get("coordination_modes") or [base_config.coordination_mode]
        return_thresholds = request.get("return_thresholds") or [base_config.return_to_base_threshold]
        candidates = []
        for strategy in strategies:
            for drone_count in drone_counts:
                for coordination_mode in coordination_modes:
                    for threshold in return_thresholds:
                        candidates.append(
                            {
                                "name": f"{strategy}-{drone_count}d-{coordination_mode}-{threshold}",
                                "strategy": strategy,
                                "drone_count": int(drone_count),
                                "coordination_mode": str(coordination_mode),
                                "return_threshold": float(threshold),
                            }
                        )
        return candidates

    @staticmethod
    def _summarize_candidate(candidate: dict[str, Any], metrics: list[Any], max_steps: int) -> dict[str, Any]:
        success_values = [1.0 if metric.mission_success else 0.0 for metric in metrics]
        detection_times = [
            float(metric.time_to_confirmed_detection or metric.time_to_detection or max_steps)
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
        score = (
            100.0 * success_rate
            - 0.8 * expected_detection_time
            - 20.0 * expected_overlap
            - 15.0 * expected_battery_risk
            - 1.5 * comms_fragility
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
            "score": round(score, 2),
            "metrics_sample": [metrics_to_summary(metric) for metric in metrics[:3]],
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
