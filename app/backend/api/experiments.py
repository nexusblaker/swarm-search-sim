"""Experiment routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.backend.api.deps import get_backend
from app.backend.api.schemas import ExperimentCreateRequest, ExperimentListResponse, ExperimentRecord
from app.backend.services import ProductBackend


router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentRecord)
def create_experiment(
    request: ExperimentCreateRequest,
    backend: ProductBackend = Depends(get_backend),
) -> ExperimentRecord:
    return ExperimentRecord(**backend.experiments.create_experiment(request.model_dump()))


@router.get("", response_model=ExperimentListResponse)
def list_experiments(backend: ProductBackend = Depends(get_backend)) -> ExperimentListResponse:
    return ExperimentListResponse(items=[ExperimentRecord(**item) for item in backend.experiments.list_experiments()])


@router.get("/{experiment_id}", response_model=ExperimentRecord)
def get_experiment(
    experiment_id: str,
    backend: ProductBackend = Depends(get_backend),
) -> ExperimentRecord:
    return ExperimentRecord(**backend.experiments.get_experiment(experiment_id))


@router.get("/{experiment_id}/summary")
def get_experiment_summary(
    experiment_id: str,
    backend: ProductBackend = Depends(get_backend),
) -> dict:
    return {"experiment_id": experiment_id, "summary": backend.experiments.load_experiment_summary(experiment_id)}
