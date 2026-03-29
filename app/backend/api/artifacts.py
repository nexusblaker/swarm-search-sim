"""Artifact file serving routes for the web frontend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.backend.api.deps import get_backend
from app.backend.services import ProductBackend


router = APIRouter(tags=["artifacts"])


@router.get("/artifacts/{owner_type}/{owner_id}/{artifact_type}")
def get_artifact(
    owner_type: str,
    owner_id: str,
    artifact_type: str,
    backend: ProductBackend = Depends(get_backend),
) -> FileResponse:
    try:
        path = backend.get_artifact_path(owner_type, owner_id, artifact_type)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path)
