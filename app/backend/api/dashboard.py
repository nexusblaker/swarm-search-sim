"""Dashboard summary routes for the React operator UI."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.backend.api.deps import get_backend
from app.backend.api.schemas import DashboardSummaryResponse
from app.backend.services import ProductBackend


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    backend: ProductBackend = Depends(get_backend),
) -> DashboardSummaryResponse:
    return DashboardSummaryResponse(**backend.get_dashboard_summary())
