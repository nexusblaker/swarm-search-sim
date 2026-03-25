"""Report routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.backend.api.deps import get_backend
from app.backend.api.schemas import ReportListResponse, ReportRecord
from app.backend.services import ProductBackend


router = APIRouter(tags=["reports"])


@router.get("/reports", response_model=ReportListResponse)
def list_reports(backend: ProductBackend = Depends(get_backend)) -> ReportListResponse:
    return ReportListResponse(items=[ReportRecord(**item) for item in backend.reports.list_reports()])


@router.post("/reports/{run_id}", response_model=ReportRecord)
def create_report(run_id: str, backend: ProductBackend = Depends(get_backend)) -> ReportRecord:
    return ReportRecord(**backend.generate_report(run_id))


@router.get("/reports/{report_id}", response_model=ReportRecord)
def get_report(report_id: str, backend: ProductBackend = Depends(get_backend)) -> ReportRecord:
    return ReportRecord(**backend.reports.get_report(report_id))
