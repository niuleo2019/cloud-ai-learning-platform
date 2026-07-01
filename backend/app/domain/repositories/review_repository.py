from abc import ABC, abstractmethod
from datetime import datetime


class ReviewRepository(ABC):
    @abstractmethod
    def list_due_today(self, user_id: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def find_by_word_id(self, user_id: int, word_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def update_review(
        self,
        user_id: int,
        word_id: int,
        review_stage: int,
        next_review_at: datetime,
        remember_level: str,
    ) -> dict:
        raise NotImplementedError
