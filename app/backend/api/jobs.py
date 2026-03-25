"""Background job routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.backend.api.deps import get_backend
from app.backend.api.schemas import JobListResponse, JobRecord
from app.backend.services import ProductBackend


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
def list_jobs(backend: ProductBackend = Depends(get_backend)) -> JobListResponse:
    return JobListResponse(items=[JobRecord(**item) for item in backend.list_jobs()])


@router.get("/{job_id}", response_model=JobRecord)
def get_job(job_id: str, backend: ProductBackend = Depends(get_backend)) -> JobRecord:
    return JobRecord(**backend.get_job(job_id))


@router.post("/{job_id}/cancel", response_model=JobRecord)
def cancel_job(job_id: str, backend: ProductBackend = Depends(get_backend)) -> JobRecord:
    return JobRecord(**backend.cancel_job(job_id))
