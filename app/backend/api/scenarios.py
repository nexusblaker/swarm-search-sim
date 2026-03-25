"""Scenario CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.backend.api.deps import get_backend
from app.backend.api.schemas import ScenarioListResponse, ScenarioPayload, ScenarioRecord
from app.backend.services import ProductBackend


router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=ScenarioListResponse)
def list_scenarios(backend: ProductBackend = Depends(get_backend)) -> ScenarioListResponse:
    return ScenarioListResponse(items=[ScenarioRecord(**item) for item in backend.scenarios.list_scenarios()])


@router.post("", response_model=ScenarioRecord)
def create_scenario(
    request: ScenarioPayload,
    backend: ProductBackend = Depends(get_backend),
) -> ScenarioRecord:
    record = backend.scenarios.create_scenario(request.model_dump())
    return ScenarioRecord(**record)


@router.get("/{scenario_id}", response_model=ScenarioRecord)
def get_scenario(
    scenario_id: str,
    backend: ProductBackend = Depends(get_backend),
) -> ScenarioRecord:
    try:
        return ScenarioRecord(**backend.scenarios.load_scenario(scenario_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{scenario_id}", response_model=ScenarioRecord)
def update_scenario(
    scenario_id: str,
    request: ScenarioPayload,
    backend: ProductBackend = Depends(get_backend),
) -> ScenarioRecord:
    record = backend.scenarios.update_scenario(scenario_id, request.model_dump())
    return ScenarioRecord(**record)


@router.delete("/{scenario_id}")
def delete_scenario(
    scenario_id: str,
    backend: ProductBackend = Depends(get_backend),
) -> dict[str, str]:
    backend.scenarios.delete_scenario(scenario_id)
    return {"status": "deleted"}
