from fastapi import APIRouter, Depends

from app.application.schemas import ReviewSubmitRequest
from app.application.services.review_service import ReviewService
from app.interfaces.http.dependencies import get_current_user, get_review_service
from app.interfaces.http.response import success_response

router = APIRouter()


@router.get("/today")
def today_reviews(
    current_user: dict = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
):
    reviews = review_service.list_today_reviews(current_user["id"])
    return success_response(reviews, "Today reviews")


@router.post("/{word_id}/submit")
def submit_review(
    word_id: int,
    payload: ReviewSubmitRequest,
    current_user: dict = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
):
    review = review_service.submit_review(current_user["id"], word_id, payload.rememberLevel)
    return success_response(review, "Review submitted")
