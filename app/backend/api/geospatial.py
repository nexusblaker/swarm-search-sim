"""Geospatial planning routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.backend.api.deps import get_backend
from app.backend.api.schemas import (
    LocationResolveRequest,
    LocationResolveResponse,
    MissionAreaPreviewRequest,
    MissionAreaPreviewResponse,
)
from app.backend.services import ProductBackend


router = APIRouter(prefix="/geo", tags=["geospatial"])


@router.post("/resolve-location", response_model=LocationResolveResponse)
def resolve_location(
    request: LocationResolveRequest,
    backend: ProductBackend = Depends(get_backend),
) -> LocationResolveResponse:
    return LocationResolveResponse(**backend.geospatial.resolve_location(request.model_dump()))


@router.post("/preview-area", response_model=MissionAreaPreviewResponse)
def preview_area(
    request: MissionAreaPreviewRequest,
    backend: ProductBackend = Depends(get_backend),
) -> MissionAreaPreviewResponse:
    return MissionAreaPreviewResponse(**backend.geospatial.preview_area(request.model_dump()))
