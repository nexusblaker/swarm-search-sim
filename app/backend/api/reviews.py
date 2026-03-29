"""After-action review routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.backend.api.deps import get_backend
from app.backend.api.schemas import AfterActionReviewListResponse, AfterActionReviewRecord, ReviewCreateRequest
from app.backend.services import ProductBackend


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=AfterActionReviewListResponse)
def list_reviews(backend: ProductBackend = Depends(get_backend)) -> AfterActionReviewListResponse:
    return AfterActionReviewListResponse(
        items=[AfterActionReviewRecord(**item) for item in backend.reviews.list_reviews()]
    )


@router.post("", response_model=AfterActionReviewRecord)
def create_review(
    request: ReviewCreateRequest,
    backend: ProductBackend = Depends(get_backend),
) -> AfterActionReviewRecord:
    return AfterActionReviewRecord(**backend.reviews.create_review(request.model_dump()))


@router.get("/{review_id}", response_model=AfterActionReviewRecord)
def get_review(review_id: str, backend: ProductBackend = Depends(get_backend)) -> AfterActionReviewRecord:
    try:
        return AfterActionReviewRecord(**backend.reviews.get_review(review_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/from-run/{run_id}", response_model=AfterActionReviewRecord)
def create_review_from_run(run_id: str, backend: ProductBackend = Depends(get_backend)) -> AfterActionReviewRecord:
    return AfterActionReviewRecord(**backend.reviews.create_from_run(run_id))

