"""Operational scenario library routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.backend.api.deps import get_backend
from app.backend.api.schemas import LibraryTemplateListResponse, LibraryTemplateRecord
from app.backend.services import ProductBackend


router = APIRouter(prefix="/library", tags=["library"])


@router.get("/templates", response_model=LibraryTemplateListResponse)
def list_library_templates(backend: ProductBackend = Depends(get_backend)) -> LibraryTemplateListResponse:
    return LibraryTemplateListResponse(
        items=[LibraryTemplateRecord(**item) for item in backend.templates.list_library_entries()]
    )


@router.get("/templates/{entry_id}", response_model=LibraryTemplateRecord)
def get_library_template(
    entry_id: str,
    backend: ProductBackend = Depends(get_backend),
) -> LibraryTemplateRecord:
    try:
        return LibraryTemplateRecord(**backend.templates.get_library_entry(entry_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
