"""Decision-support routes for comparison and recommendation."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.backend.api.deps import get_backend
from app.backend.api.schemas import ComparePlansRequest, ComparePlansResponse, RecommendRequest, RecommendResponse
from app.backend.services import ProductBackend


router = APIRouter(tags=["decision-support"])


@router.post("/compare-plans", response_model=ComparePlansResponse)
def compare_plans(
    request: ComparePlansRequest,
    backend: ProductBackend = Depends(get_backend),
) -> ComparePlansResponse:
    return ComparePlansResponse(**backend.comparison.compare(request.model_dump()))


@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    request: RecommendRequest,
    backend: ProductBackend = Depends(get_backend),
) -> RecommendResponse:
    return RecommendResponse(**backend.recommendations.recommend(request.model_dump()))
