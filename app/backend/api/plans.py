"""Mission plan routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.backend.api.deps import get_backend
from app.backend.api.schemas import MissionPlanCreateRequest, MissionPlanListResponse, MissionPlanRecord
from app.backend.services import ProductBackend


router = APIRouter(prefix="/plans", tags=["plans"])


def _to_plan_record(item: dict[str, object]) -> MissionPlanRecord:
    summary = item.get("summary_json", {}) if isinstance(item, dict) else {}
    summary = summary if isinstance(summary, dict) else {}
    return MissionPlanRecord(
        **item,
        asset_package=summary.get("asset_package"),
        mission_intent=summary.get("mission_intent"),
        intake_summary=summary.get("intake_summary", {}),
    )


@router.get("", response_model=MissionPlanListResponse)
def list_plans(backend: ProductBackend = Depends(get_backend)) -> MissionPlanListResponse:
    return MissionPlanListResponse(items=[_to_plan_record(item) for item in backend.plans.list_plans()])


@router.post("", response_model=MissionPlanRecord)
def create_plan(
    request: MissionPlanCreateRequest,
    backend: ProductBackend = Depends(get_backend),
) -> MissionPlanRecord:
    return _to_plan_record(backend.plans.create_plan(request.model_dump()))


@router.get("/{plan_id}", response_model=MissionPlanRecord)
def get_plan(plan_id: str, backend: ProductBackend = Depends(get_backend)) -> MissionPlanRecord:
    try:
        return _to_plan_record(backend.plans.get_plan(plan_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{plan_id}", response_model=MissionPlanRecord)
def update_plan(
    plan_id: str,
    request: MissionPlanCreateRequest,
    backend: ProductBackend = Depends(get_backend),
) -> MissionPlanRecord:
    return _to_plan_record(backend.plans.update_plan(plan_id, request.model_dump()))


@router.delete("/{plan_id}")
def delete_plan(plan_id: str, backend: ProductBackend = Depends(get_backend)) -> dict[str, str]:
    backend.plans.delete_plan(plan_id)
    return {"status": "deleted"}
