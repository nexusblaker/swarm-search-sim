"""Health routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.backend.api.deps import get_backend
from app.backend.api.schemas import HealthResponse
from app.backend.services import ProductBackend


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(backend: ProductBackend = Depends(get_backend)) -> HealthResponse:
    return HealthResponse(**backend.get_health())
