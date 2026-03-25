"""Template browsing routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.backend.api.deps import get_backend
from app.backend.api.schemas import TemplateListResponse, TemplateRecord
from app.backend.services import ProductBackend


router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
def list_templates(backend: ProductBackend = Depends(get_backend)) -> TemplateListResponse:
    return TemplateListResponse(items=[TemplateRecord(**item) for item in backend.templates.list_templates()])


@router.get("/{template_id}", response_model=TemplateRecord)
def get_template(
    template_id: str,
    backend: ProductBackend = Depends(get_backend),
) -> TemplateRecord:
    try:
        return TemplateRecord(**backend.templates.get_template(template_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
