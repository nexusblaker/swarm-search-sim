"""Saved plan comparison routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.backend.api.deps import get_backend
from app.backend.api.schemas import PlanComparisonListResponse, PlanComparisonRecord, RunCreateRequest, RunRecord, SavedComparisonCreateRequest
from app.backend.services import ProductBackend


router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.get("", response_model=PlanComparisonListResponse)
def list_comparisons(backend: ProductBackend = Depends(get_backend)) -> PlanComparisonListResponse:
    return PlanComparisonListResponse(
        items=[PlanComparisonRecord(**item) for item in backend.comparisons.list_comparisons()]
    )


@router.post("", response_model=PlanComparisonRecord)
def create_comparison(
    request: SavedComparisonCreateRequest,
    backend: ProductBackend = Depends(get_backend),
) -> PlanComparisonRecord:
    return PlanComparisonRecord(**backend.comparisons.create_comparison(request.model_dump()))


@router.get("/{comparison_id}", response_model=PlanComparisonRecord)
def get_comparison(
    comparison_id: str,
    backend: ProductBackend = Depends(get_backend),
) -> PlanComparisonRecord:
    try:
        return PlanComparisonRecord(**backend.comparisons.get_comparison(comparison_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{comparison_id}/run", response_model=RunRecord)
def launch_run_from_comparison(
    comparison_id: str,
    request: RunCreateRequest,
    backend: ProductBackend = Depends(get_backend),
) -> RunRecord:
    run_request = request.model_dump()
    run_request["comparison_id"] = comparison_id
    return RunRecord(**backend.missions.create_run(run_request))


@router.get("/{comparison_id}/summary")
def get_comparison_summary(comparison_id: str, backend: ProductBackend = Depends(get_backend)) -> dict:
    return backend.comparisons.get_summary(comparison_id)

