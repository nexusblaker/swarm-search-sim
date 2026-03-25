"""FastAPI dependencies for shared backend services."""

from __future__ import annotations

from fastapi import Request

from app.backend.services import ProductBackend


def get_backend(request: Request) -> ProductBackend:
    """Return the product backend singleton from FastAPI app state."""

    return request.app.state.backend
