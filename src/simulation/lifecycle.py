"""Battery reserve profiles and lifecycle labels for mission execution."""

from __future__ import annotations

from dataclasses import dataclass


LIFECYCLE_DEPLOYING = "deploying"
LIFECYCLE_SEARCHING = "searching"
LIFECYCLE_RETURNING = "returning_to_base"
LIFECYCLE_RECHARGING = "recharging_or_swapping"
LIFECYCLE_READY = "ready_to_redeploy"
LIFECYCLE_REDEPLOYING = "redeploying"
LIFECYCLE_UNAVAILABLE = "unavailable"

RESERVE_SAFE = "safe"
RESERVE_APPROACHING = "approaching_reserve_limit"
RESERVE_RETURNING = "returning_now"
RESERVE_CRITICAL = "critical_battery_margin"


@dataclass(frozen=True, slots=True)
class ReserveProfile:
    """Operator-facing reserve posture mapped to sim-friendly margins."""

    name: str
    floor_multiplier: float
    contingency_ratio: float
    warning_ratio: float
    critical_ratio: float
    range_pressure_ratio: float


@dataclass(frozen=True, slots=True)
class BatteryDecision:
    """Path-aware battery decision for one drone at one step."""

    energy_to_base: float
    energy_to_base_from_next: float
    reserve_required: float
    return_required: float
    continue_required: float
    warning_required: float
    critical_required: float
    battery_margin: float
    return_eta_steps: int
    reserve_status: str
    should_return: bool
    critical: bool
    reason: str


RESERVE_PROFILES: dict[str, ReserveProfile] = {
    "aggressive": ReserveProfile(
        name="aggressive",
        floor_multiplier=0.85,
        contingency_ratio=0.15,
        warning_ratio=0.12,
        critical_ratio=0.08,
        range_pressure_ratio=0.10,
    ),
    "balanced": ReserveProfile(
        name="balanced",
        floor_multiplier=1.0,
        contingency_ratio=0.24,
        warning_ratio=0.20,
        critical_ratio=0.12,
        range_pressure_ratio=0.15,
    ),
    "conservative": ReserveProfile(
        name="conservative",
        floor_multiplier=1.15,
        contingency_ratio=0.34,
        warning_ratio=0.28,
        critical_ratio=0.18,
        range_pressure_ratio=0.22,
    ),
}


LIFECYCLE_LABELS = {
    LIFECYCLE_DEPLOYING: "Deploying",
    LIFECYCLE_SEARCHING: "Searching",
    LIFECYCLE_RETURNING: "Returning to Base",
    LIFECYCLE_RECHARGING: "Recharging",
    LIFECYCLE_READY: "Ready to Redeploy",
    LIFECYCLE_REDEPLOYING: "Redeploying",
    LIFECYCLE_UNAVAILABLE: "Unavailable",
}

RESERVE_STATUS_LABELS = {
    RESERVE_SAFE: "Safe",
    RESERVE_APPROACHING: "Approaching Reserve Limit",
    RESERVE_RETURNING: "Returning Now",
    RESERVE_CRITICAL: "Critical Battery Margin",
}


def resolve_reserve_profile(preset: str | None) -> ReserveProfile:
    """Return a known reserve profile, falling back to balanced."""

    normalized = str(preset or "balanced").strip().lower().replace(" ", "_")
    return RESERVE_PROFILES.get(normalized, RESERVE_PROFILES["balanced"])


def lifecycle_label(state: str) -> str:
    """Return a readable operator label for a lifecycle state."""

    return LIFECYCLE_LABELS.get(state, state.replace("_", " ").title())


def reserve_status_label(state: str) -> str:
    """Return a readable operator label for a reserve status."""

    return RESERVE_STATUS_LABELS.get(state, state.replace("_", " ").title())
