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


class RunCreateRequest(BaseModel):
    scenario_id: str | None = None
    template_id: str | None = None
    scenario: dict[str, Any] | None = None
    seed: int | None = None


class RunRecord(BaseModel):
    id: str
    scenario_id: str
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


class RecommendRequest(BaseModel):
    scenario_id: str | None = None
    scenario: dict[str, Any] | None = None
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
    explanation: str
    candidate_plans: list[dict[str, Any]]
