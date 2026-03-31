"""Shared sensing workflow models for cue, inspect, and confirm behavior."""

from __future__ import annotations

from dataclasses import dataclass, field


Position = tuple[int, int]

SENSING_SEARCHING = "searching"
SENSING_CUE_DETECTED = "cue_detected"
SENSING_INSPECTING = "inspecting_contact"
SENSING_CONFIRMATION_PENDING = "confirmation_pending"
SENSING_CONFIRMED = "confirmed_contact"
SENSING_REJECTED = "false_alarm_rejected"
SENSING_RESUMED = "search_resumed"

CONTACT_CUE = "cue_detected"
CONTACT_INSPECTING = "inspecting_contact"
CONTACT_CONFIRMATION_PENDING = "confirmation_pending"
CONTACT_CONFIRMED = "contact_confirmed"
CONTACT_REJECTED = "false_alarm_rejected"

INSPECTION_CONFIRMED = "confirmed"
INSPECTION_REJECTED = "rejected"
INSPECTION_PENDING = "pending"


@dataclass(slots=True)
class ContactSignal:
    """A possible contact produced by a broad-search scan."""

    position: Position
    confidence: float
    candidate_score: float
    requires_inspection: bool
    is_true_target: bool
    false_positive: bool
    distance: float
    terrain_modifier: float
    weather_factor: float
    source_channels: dict[str, float]
    note: str


@dataclass(slots=True)
class InspectionOutcome:
    """The result of a close inspection pass on a candidate contact."""

    outcome: str
    confidence: float
    distance: float
    note: str


@dataclass(slots=True)
class TrackedContact:
    """A candidate contact tracked through cue, inspection, and resolution."""

    id: str
    position: Position
    status: str
    confidence: float
    candidate_score: float
    cue_step: int
    detecting_drone_id: int | None
    assigned_drone_id: int | None = None
    source_channels: dict[str, float] = field(default_factory=dict)
    is_true_target: bool = False
    false_positive: bool = False
    distance: float = 0.0
    terrain_modifier: float = 1.0
    weather_factor: float = 1.0
    note: str = ""
    last_update_step: int = 0
    inspect_started_step: int | None = None
    inspect_completed_step: int | None = None
    resolution_step: int | None = None
    inspection_attempts: int = 0
    resolved: bool = False
    outcome: str | None = None
    confidence_history: list[float] = field(default_factory=list)


def sensing_label(state: str) -> str:
    """Return an operator-facing label for a sensing state."""

    labels = {
        SENSING_SEARCHING: "Searching",
        SENSING_CUE_DETECTED: "Possible Contact",
        SENSING_INSPECTING: "Inspecting Contact",
        SENSING_CONFIRMATION_PENDING: "Confirmation Pending",
        SENSING_CONFIRMED: "Contact Confirmed",
        SENSING_REJECTED: "False Alarm Rejected",
        SENSING_RESUMED: "Search Resumed",
    }
    return labels.get(state, state.replace("_", " ").title())


def contact_label(status: str) -> str:
    """Return an operator-facing label for a tracked contact."""

    labels = {
        CONTACT_CUE: "Possible Contact",
        CONTACT_INSPECTING: "Inspecting Contact",
        CONTACT_CONFIRMATION_PENDING: "Confirmation Pending",
        CONTACT_CONFIRMED: "Contact Confirmed",
        CONTACT_REJECTED: "False Alarm Rejected",
    }
    return labels.get(status, status.replace("_", " ").title())
