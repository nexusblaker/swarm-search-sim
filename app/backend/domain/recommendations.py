"""Explainable recommendation services."""

from __future__ import annotations

from typing import Any, Callable

from app.backend.domain.comparisons import ComparisonEvaluator


class RecommendationService:
    """Explainable mission recommendations using lightweight comparison logic."""

    def __init__(
        self,
        evaluator: ComparisonEvaluator,
        resolve_plan_json: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self.evaluator = evaluator
        self.resolve_plan_json = resolve_plan_json

    def recommend(self, request: dict[str, Any]) -> dict[str, Any]:
        if request.get("plan_id") and self.resolve_plan_json is not None:
            request = dict(request)
            request.setdefault("plan_json", self.resolve_plan_json(str(request["plan_id"])))
        comparison = self.evaluator.compare(
            {
                **request,
                "strategies": request.get("strategies")
                or ["information_gain", "auction_based", "probability_greedy", "sector_search"],
                "drone_counts": request.get("drone_counts"),
                "coordination_modes": request.get("coordination_modes"),
                "return_thresholds": request.get("return_thresholds"),
                "num_seeds": request.get("num_seeds", 2),
            }
        )
        top = comparison["top_recommendation"]
        explanation = (
            f"Recommend {top.get('strategy')} with {top.get('drone_count')} drones and "
            f"return threshold {top.get('return_threshold')} because it balances "
            f"success rate, detection time, battery margin, overlap, and comms fragility."
        )
        return {
            "recommended_strategy": top.get("strategy"),
            "recommended_drone_count": top.get("drone_count"),
            "recommended_return_threshold": top.get("return_threshold"),
            "risk_summary": {
                "overall_risk": "moderate" if top.get("expected_success_rate", 0.0) >= 0.5 else "elevated",
                "battery_risk": top.get("expected_battery_risk"),
                "battery_margin_band": top.get("battery_margin_band", {}),
                "overlap_risk": top.get("expected_overlap"),
                "communications_fragility": top.get("communications_fragility"),
                "failure_modes": top.get("failure_modes", []),
                "confidence_basis": comparison["confidence_summary"],
            },
            "uncertainty_summary": comparison.get("uncertainty_summary", {}),
            "explanation": explanation,
            "recommendation_snapshot": {
                "top_recommendation": top,
                "confidence_summary": comparison["confidence_summary"],
                "uncertainty_summary": comparison.get("uncertainty_summary", {}),
                "sensitivity_summary": comparison.get("sensitivity_summary", {}),
            },
            "candidate_plans": comparison["ranked_plans"],
        }
