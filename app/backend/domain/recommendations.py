"""Explainable recommendation services."""

from __future__ import annotations

from typing import Any, Callable

from app.backend.domain.assets import apply_asset_package_to_payload
from app.backend.domain.comparisons import ComparisonEvaluator


class RecommendationService:
    """Explainable mission recommendations using lightweight comparison logic."""

    INTENT_LABELS = {
        "broad_area_coverage": "broad area coverage",
        "fast_containment": "fast containment",
        "high_confidence_confirmation": "high-confidence confirmation",
        "battery_conservative": "battery-conservative search",
    }

    STRATEGY_LABELS = {
        "sector_search": "a broad area sweep",
        "auction_based": "a fast containment pattern",
        "information_gain": "a focused confirmation search",
        "probability_greedy": "a probability-led search",
        "random_sweep": "an exploratory sweep",
    }

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
        payload = request.get("scenario") or request.get("plan_json")
        asset_package = request.get("asset_package")
        if isinstance(payload, dict):
            enriched_payload, normalized_assets = apply_asset_package_to_payload(
                payload,
                asset_package or payload.get("scenario", {}).get("asset_package"),
            )
            request = dict(request)
            if request.get("scenario") is not None:
                request["scenario"] = enriched_payload
            if request.get("plan_json") is not None:
                request["plan_json"] = enriched_payload
            asset_package = normalized_assets
        comparison = self.evaluator.compare(
            {
                **request,
                "strategies": request.get("strategies"),
                "drone_counts": request.get("drone_counts"),
                "coordination_modes": request.get("coordination_modes"),
                "return_thresholds": request.get("return_thresholds"),
                "num_seeds": request.get("num_seeds", 2),
            }
        )
        top = comparison["top_recommendation"]
        alternative = comparison["ranked_plans"][1] if len(comparison["ranked_plans"]) > 1 else None
        mission_intent = str(request.get("mission_intent") or comparison.get("mission_intent") or "broad_area_coverage")
        asset_package = asset_package or comparison.get("asset_package") or {}
        team_coordination_label = str(top.get("team_coordination_label") or self._coordination_label(top.get("coordination_mode")))
        explanation = self._build_explanation(top, mission_intent)
        concise_summary = self._build_concise_summary(top, alternative, asset_package, mission_intent)
        key_tradeoffs = self._build_tradeoffs(top, alternative)
        key_risks = self._build_risks(top, mission_intent)
        return {
            "recommended_strategy": top.get("strategy"),
            "recommended_search_pattern": top.get("search_pattern"),
            "recommended_search_pattern_label": top.get("search_pattern_label"),
            "search_pattern_summary": top.get("search_pattern_summary"),
            "search_pattern_reason": top.get("search_pattern_reason"),
            "search_pattern_fit_summary": top.get("search_pattern_fit_summary"),
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
            "concise_summary": concise_summary,
            "top_alternative_summary": self._build_alternative_summary(alternative) if alternative else None,
            "key_tradeoffs": key_tradeoffs,
            "key_risks": key_risks,
            "team_coordination_label": team_coordination_label,
            "asset_package": asset_package,
            "technical_details": {
                "operator_fit_summary": top.get("operator_fit_summary"),
                "mission_area_summary": top.get("mission_area_summary"),
                "mission_area": top.get("mission_area"),
                "search_pattern_geometry": top.get("search_pattern_geometry"),
                "sensing_conditions_summary": top.get("sensing_conditions_summary"),
                "inspection_burden": top.get("inspection_burden"),
                "mission_intent": mission_intent,
                "confidence_summary": comparison["confidence_summary"],
                "sensitivity_summary": comparison.get("sensitivity_summary", {}),
            },
            "recommendation_snapshot": {
                "top_recommendation": top,
                "confidence_summary": comparison["confidence_summary"],
                "uncertainty_summary": comparison.get("uncertainty_summary", {}),
                "sensitivity_summary": comparison.get("sensitivity_summary", {}),
                "concise_summary": concise_summary,
                "top_alternative_summary": self._build_alternative_summary(alternative) if alternative else None,
                "key_tradeoffs": key_tradeoffs,
                "key_risks": key_risks,
                "team_coordination_label": team_coordination_label,
                "asset_package": asset_package,
            },
            "candidate_plans": comparison["ranked_plans"],
        }

    def _build_explanation(self, top: dict[str, Any], mission_intent: str) -> str:
        strategy_label = self.STRATEGY_LABELS.get(str(top.get("strategy")), str(top.get("strategy") or "this search style"))
        pattern_label = str(top.get("search_pattern_label") or "this search pattern")
        intent_label = self.INTENT_LABELS.get(mission_intent, mission_intent.replace("_", " "))
        area_summary = str(top.get("mission_area_summary") or "").strip()
        context_note = self._context_note(top)
        return (
            f"{pattern_label} is the best fit for the requested {intent_label}. "
            f"It uses {strategy_label} underneath with {top.get('drone_count')} drones and a "
            f"{top.get('return_threshold')}% return reserve so coverage geometry, battery margin, and confirmation tempo stay aligned."
            f"{f' {area_summary}' if area_summary else ''}"
            f"{f' {context_note}' if context_note else ''}"
        )

    def _build_concise_summary(
        self,
        top: dict[str, Any],
        alternative: dict[str, Any] | None,
        asset_package: dict[str, Any],
        mission_intent: str,
    ) -> str:
        pattern_label = str(top.get("search_pattern_label") or "a recommended search pattern")
        staging = asset_package.get("staging_location")
        staging_text = f" from the {staging}" if staging else ""
        area_summary = str(top.get("mission_area_summary") or "").strip()
        fleet = asset_package.get("fleet_composition", {})
        fleet_text = f"{int(fleet.get('total_drones') or top.get('drone_count') or 0)} mixed-range drones"
        if fleet.get("drone_type_count", 1) <= 1:
            fleet_text = f"{top.get('drone_count')} drones"
        intent_label = self.INTENT_LABELS.get(mission_intent, mission_intent.replace("_", " "))
        reason = str(top.get("search_pattern_reason") or "").strip()
        tradeoff = ""
        if alternative:
            tradeoff = (
                f" It edges out the main alternative by offering better "
                f"{'battery margin' if float(top.get('expected_battery_risk', 0.0)) <= float(alternative.get('expected_battery_risk', 1.0)) else 'coverage speed'}."
            )
        context_note = self._context_note(top)
        sensing_note = ""
        if str(top.get("inspection_burden", "")) == "elevated":
            sensing_note = " Expect more inspect passes before confirmation."
        elif mission_intent == "high_confidence_confirmation":
            sensing_note = " It favors deliberate cue-to-confirm inspection over the fastest possible sweep."
        return (
            f"Recommended: use {pattern_label} with {fleet_text}{staging_text}. "
            f"{reason or f'This gives the best balance for {intent_label}.'}"
            f"{f' {area_summary}' if area_summary else ''}"
            f"{f' {context_note}' if context_note else ''}{tradeoff}{sensing_note}"
        )

    def _build_alternative_summary(self, alternative: dict[str, Any]) -> str:
        pattern_label = str(
            alternative.get("search_pattern_label")
            or self.STRATEGY_LABELS.get(str(alternative.get("strategy")), str(alternative.get("strategy") or "alternative plan"))
        )
        return (
            f"Alternative: {pattern_label} with {alternative.get('drone_count')} drones. "
            f"{alternative.get('search_pattern_reason') or 'It stays viable, but gives up some margin on speed, confidence, or reserve.'}"
        )

    def _build_tradeoffs(self, top: dict[str, Any], alternative: dict[str, Any] | None) -> list[str]:
        tradeoffs = [str(item) for item in top.get("key_tradeoffs", []) if item]
        if alternative:
            if float(top.get("expected_detection_time", 0.0)) > float(alternative.get("expected_detection_time", 10_000.0)):
                tradeoffs.append("slightly slower than the top alternative, but with a steadier risk picture")
            if float(top.get("expected_battery_risk", 1.0)) < float(alternative.get("expected_battery_risk", 1.0)):
                tradeoffs.append("holds more battery margin than the top alternative")
        if top.get("sensing_conditions_summary"):
            tradeoffs.append(str(top["sensing_conditions_summary"]))
        return tradeoffs[:3] or ["balances speed, confidence, and reserve without leaning too hard on one factor"]

    def _build_risks(self, top: dict[str, Any], mission_intent: str) -> list[str]:
        risks = [str(item) for item in top.get("failure_modes", []) if item and item != "no major failure mode flagged"]
        if not risks:
            risks.append("no major operational risk was flagged in the short evaluation bundle")
        if mission_intent == "fast_containment" and float(top.get("expected_battery_risk", 0.0)) >= 0.3:
            risks.append("faster containment tempo leaves less reserve for re-tasking")
        if str(top.get("inspection_burden", "")) == "elevated":
            risks.append("reduced visibility may create more low-confidence contacts that need inspection")
        return risks[:3]

    @staticmethod
    def _context_note(top: dict[str, Any]) -> str:
        mission_area = top.get("mission_area") or {}
        if not isinstance(mission_area, dict):
            return ""
        weather_summary = mission_area.get("weather_summary") or {}
        wind_speed = float(weather_summary.get("wind_speed_kph", 0.0) or 0.0)
        weather_label = str(weather_summary.get("condition_label") or "").strip()
        has_precise_last_known = bool(
            isinstance(mission_area.get("last_known_location"), dict)
            and mission_area["last_known_location"].get("latitude") is not None
            and mission_area["last_known_location"].get("longitude") is not None
        )
        if has_precise_last_known and str(top.get("search_pattern")) == "expanding_ring":
            return "The placed last known point lets the opening search stay anchored instead of treating the mission as a wide sweep."
        if wind_speed >= 24.0 and weather_label:
            return f"{weather_label} conditions are already folded into the search pacing and reserve margins."
        if str(top.get("search_pattern")) == "broad_area_sweep" and mission_area.get("last_known_status") == "unknown":
            return "The area is being treated as a wide uncertainty search rather than a point-focused task."
        return ""

    @staticmethod
    def _coordination_label(mode: Any) -> str:
        if str(mode) == "decentralized":
            return "distributed team coordination"
        return "guided from a single mission desk"
