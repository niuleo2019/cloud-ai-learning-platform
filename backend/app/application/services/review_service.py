from app.domain.repositories.review_repository import ReviewRepository
from app.domain.services.review_policy import ReviewPolicy
from app.interfaces.exceptions import AppException


class ReviewService:
    """应用服务：处理今日复习和提交复习结果。"""

    def __init__(self, review_repository: ReviewRepository, review_policy: ReviewPolicy):
        self.review_repository = review_repository
        self.review_policy = review_policy

    def list_today_reviews(self, user_id: int) -> list[dict]:
        return self.review_repository.list_due_today(user_id)

    def submit_review(self, user_id: int, word_id: int, remember_level: str) -> dict:
        review = self.review_repository.find_by_word_id(user_id, word_id)
        if not review:
            raise AppException(code=40420, message="Review record not found", status_code=404)

        try:
            next_stage, next_review_at = self.review_policy.calculate(
                review["review_stage"],
                remember_level,
            )
        except ValueError as error:
            raise AppException(code=40020, message=str(error), status_code=400) from error

        return self.review_repository.update_review(
            user_id=user_id,
            word_id=word_id,
            review_stage=next_stage,
            next_review_at=next_review_at,
            remember_level=remember_level,
        )
