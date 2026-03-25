"""Run, intervention, replay, and event routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.backend.api.deps import get_backend
from app.backend.api.schemas import (
    EventsResponse,
    InterventionRequest,
    ReplayResponse,
    RunCreateRequest,
    RunListResponse,
    RunRecord,
)
from app.backend.services import ProductBackend


router = APIRouter(tags=["runs"])


@router.post("/runs", response_model=RunRecord)
def create_run(
    request: RunCreateRequest,
    backend: ProductBackend = Depends(get_backend),
) -> RunRecord:
    return RunRecord(**backend.missions.create_run(request.model_dump()))


@router.get("/runs", response_model=RunListResponse)
def list_runs(backend: ProductBackend = Depends(get_backend)) -> RunListResponse:
    return RunListResponse(items=[RunRecord(**item) for item in backend.missions.list_runs()])


@router.get("/runs/{run_id}", response_model=RunRecord)
def get_run(run_id: str, backend: ProductBackend = Depends(get_backend)) -> RunRecord:
    try:
        return RunRecord(**backend.missions.get_run(run_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/runs/{run_id}/interventions")
def apply_intervention(
    run_id: str,
    request: InterventionRequest,
    backend: ProductBackend = Depends(get_backend),
) -> dict:
    return backend.missions.apply_intervention(run_id, request.action, request.payload)


@router.get("/runs/{run_id}/replay", response_model=ReplayResponse)
def get_replay(run_id: str, backend: ProductBackend = Depends(get_backend)) -> ReplayResponse:
    return ReplayResponse(run_id=run_id, replay=backend.missions.get_replay(run_id))


@router.get("/runs/{run_id}/events", response_model=EventsResponse)
def get_events(run_id: str, backend: ProductBackend = Depends(get_backend)) -> EventsResponse:
    return EventsResponse(run_id=run_id, events=backend.missions.get_events(run_id))
