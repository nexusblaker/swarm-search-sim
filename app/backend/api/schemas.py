"""Pydantic request and response models for the product API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database_path: str
    storage_root: str


class ScenarioPayload(BaseModel):
    scenario: dict[str, Any]


class ScenarioRecord(BaseModel):
    id: str
    name: str
    type: str
    created_at: float
    updated_at: float
    deleted_at: float | None = None
    config_json: dict[str, Any]
    summary_json: dict[str, Any]
    file_path: str | None = None


class ScenarioListResponse(BaseModel):
    items: list[ScenarioRecord]


class TemplateRecord(BaseModel):
    id: str
    name: str
    family: str
    description: str
    created_at: float
    updated_at: float
    config_json: dict[str, Any]
    summary_json: dict[str, Any]
    file_path: str | None = None


class TemplateListResponse(BaseModel):
    items: list[TemplateRecord]


class LibraryTemplateRecord(BaseModel):
    id: str
    template_id: str
    name: str
    family: str
    doctrine_type: str
    description: str
    intended_use: str
    recommended_strategies_json: list[str]
    risks_json: list[str]
    assumptions_json: list[str]
    tags_json: list[str]
    config_json: dict[str, Any]
    summary_json: dict[str, Any]
    file_path: str | None = None


class LibraryTemplateListResponse(BaseModel):
    items: list[LibraryTemplateRecord]


class MissionPlanCreateRequest(BaseModel):
    name: str
    scenario_id: str | None = None
    template_id: str | None = None
    scenario: dict[str, Any] | None = None
    plan_json: dict[str, Any] | None = None
    strategy: str | None = None
    num_drones: int | None = None
    weather: str | None = None
    target_behavior: str | None = None
    asset_package: dict[str, Any] = Field(default_factory=dict)
    reserve_policy: dict[str, Any] = Field(default_factory=dict)
    communication_assumptions: dict[str, Any] = Field(default_factory=dict)
    map_selection: dict[str, Any] = Field(default_factory=dict)
    priority_zones: list[dict[str, Any]] = Field(default_factory=list)
    exclusion_zones: list[dict[str, Any]] = Field(default_factory=list)
    candidate_alternatives: list[dict[str, Any]] = Field(default_factory=list)
    operator_notes: str = ""
    approval_state: str = "draft"
    recommendation_snapshot: dict[str, Any] | None = None
    recommendation_num_seeds: int = 1


class MissionPlanRecord(BaseModel):
    id: str
    name: str
    scenario_id: str | None = None
    template_id: str | None = None
    approval_state: str
    created_at: float
    updated_at: float
    deleted_at: float | None = None
    plan_json: dict[str, Any]
    summary_json: dict[str, Any]
    recommendation_json: dict[str, Any]
    operator_notes: str
    candidate_alternatives_json: list[dict[str, Any]]
    priority_zones_json: list[dict[str, Any]]
    exclusion_zones_json: list[dict[str, Any]]
    latest_comparison_id: str | None = None
    latest_review_id: str | None = None
    linked_run_ids_json: list[str]


class MissionPlanListResponse(BaseModel):
    items: list[MissionPlanRecord]


class RunCreateRequest(BaseModel):
    scenario_id: str | None = None
    template_id: str | None = None
    plan_id: str | None = None
    comparison_id: str | None = None
    candidate_id: str | None = None
    scenario: dict[str, Any] | None = None
    seed: int | None = None


class RunRecord(BaseModel):
    id: str
    scenario_id: str
    plan_id: str | None = None
    comparison_id: str | None = None
    candidate_id: str | None = None
    status: str
    created_at: float
    updated_at: float
    completed_at: float | None = None
    config_json: dict[str, Any]
    summary_json: dict[str, Any]
    latest_snapshot_json: dict[str, Any] | None = None
    output_dir: str
    job_id: str | None = None
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    job: dict[str, Any] | None = None
    interventions: list[dict[str, Any]] = Field(default_factory=list)


class RunListResponse(BaseModel):
    items: list[RunRecord]


class InterventionRequest(BaseModel):
    action: str
    payload: dict[str, Any] | None = None


class ReplayResponse(BaseModel):
    run_id: str
    replay: list[dict[str, Any]]


class EventsResponse(BaseModel):
    run_id: str
    events: list[dict[str, Any]]


class ExperimentCreateRequest(BaseModel):
    strategies: list[str] | None = None
    scenario_families: list[str] | None = None
    target_behaviors: list[str] | None = None
    coordination_modes: list[str] | None = None
    drone_counts: list[int] | None = None
    battery_budgets: list[float] | None = None
    sensor_modes: list[str] | None = None
    benchmark_num_seeds: int = 4
    experiment_num_seeds: int = 1


class ExperimentRecord(BaseModel):
    id: str
    status: str
    created_at: float
    updated_at: float
    completed_at: float | None = None
    request_json: dict[str, Any]
    summary_json: list[dict[str, Any]] | dict[str, Any]
    output_dir: str
    job_id: str | None = None
    error: str | None = None
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    job: dict[str, Any] | None = None


class ExperimentListResponse(BaseModel):
    items: list[ExperimentRecord]


class ComparisonCandidateInput(BaseModel):
    name: str | None = None
    strategy: str | None = None
    drone_count: int | None = None
    coordination_mode: str | None = None
    return_threshold: float | None = None


class SavedComparisonCreateRequest(BaseModel):
    name: str | None = None
    plan_id: str | None = None
    scenario_id: str | None = None
    scenario: dict[str, Any] | None = None
    candidate_plans: list[ComparisonCandidateInput] | None = None
    strategies: list[str] | None = None
    drone_counts: list[int] | None = None
    coordination_modes: list[str] | None = None
    return_thresholds: list[float] | None = None
    num_seeds: int = 2


class PlanCandidateRecord(BaseModel):
    id: str
    comparison_id: str
    name: str
    rank: int
    linked_run_id: str | None = None
    config_json: dict[str, Any]
    summary_json: dict[str, Any]


class PlanComparisonRecord(BaseModel):
    id: str
    plan_id: str | None = None
    name: str
    status: str
    created_at: float
    updated_at: float
    completed_at: float | None = None
    request_json: dict[str, Any]
    summary_json: list[dict[str, Any]]
    recommendation_json: dict[str, Any]
    uncertainty_json: dict[str, Any]
    sensitivity_json: dict[str, Any]
    linked_run_ids_json: list[str]
    report_id: str | None = None
    job_id: str | None = None
    candidates: list[PlanCandidateRecord] = Field(default_factory=list)


class PlanComparisonListResponse(BaseModel):
    items: list[PlanComparisonRecord]


class JobRecord(BaseModel):
    id: str
    job_type: str
    owner_type: str
    owner_id: str
    status: str
    progress: float
    created_at: float
    updated_at: float
    completed_at: float | None = None
    error: str | None = None
    summary_json: dict[str, Any]


class JobListResponse(BaseModel):
    items: list[JobRecord]


class ReportRecord(BaseModel):
    id: str
    run_id: str
    owner_type: str = "run"
    owner_id: str | None = None
    report_type: str
    created_at: float
    summary_json: dict[str, Any]
    file_path: str


class ReportListResponse(BaseModel):
    items: list[ReportRecord]


class ComparePlansRequest(BaseModel):
    scenario_id: str | None = None
    scenario: dict[str, Any] | None = None
    strategies: list[str] | None = None
    drone_counts: list[int] | None = None
    coordination_modes: list[str] | None = None
    return_thresholds: list[float] | None = None
    num_seeds: int = 2


class ComparePlansResponse(BaseModel):
    ranked_plans: list[dict[str, Any]]
    top_recommendation: dict[str, Any]
    confidence_summary: dict[str, Any]
    uncertainty_summary: dict[str, Any] = Field(default_factory=dict)
    sensitivity_summary: dict[str, Any] = Field(default_factory=dict)


class RecommendRequest(BaseModel):
    scenario_id: str | None = None
    scenario: dict[str, Any] | None = None
    plan_id: str | None = None
    strategies: list[str] | None = None
    drone_counts: list[int] | None = None
    coordination_modes: list[str] | None = None
    return_thresholds: list[float] | None = None
    num_seeds: int = 2


class RecommendResponse(BaseModel):
    recommended_strategy: str | None = None
    recommended_drone_count: int | None = None
    recommended_return_threshold: float | None = None
    risk_summary: dict[str, Any]
    uncertainty_summary: dict[str, Any] = Field(default_factory=dict)
    explanation: str
    recommendation_snapshot: dict[str, Any] = Field(default_factory=dict)
    candidate_plans: list[dict[str, Any]]


class ReviewCreateRequest(BaseModel):
    run_id: str
    name: str | None = None


class AfterActionReviewRecord(BaseModel):
    id: str
    run_id: str
    plan_id: str | None = None
    comparison_id: str | None = None
    name: str
    created_at: float
    updated_at: float
    summary_json: dict[str, Any]
    timeline_json: dict[str, Any]
    alternate_plan_json: dict[str, Any]
    report_id: str | None = None
    report: dict[str, Any] | None = None


class AfterActionReviewListResponse(BaseModel):
    items: list[AfterActionReviewRecord]
