from abc import ABC, abstractmethod
from datetime import date


class PracticeRepository(ABC):
    @abstractmethod
    def record(self, user_id: int, attempt: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def recent(self, user_id: int, days: int) -> list[dict]:
        """Attempts in the last `days` days, newest first, with the material title."""
        raise NotImplementedError


class StudyPlanRepository(ABC):
    @abstractmethod
    def find(self, user_id: int, plan_date: date) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, user_id: int, plan_date: date, summary: str, tasks: list[dict], model: str | None) -> dict:
        """Insert, or replace the plan for that day (done marks are reset)."""
        raise NotImplementedError

    @abstractmethod
    def set_done(self, user_id: int, plan_date: date, done: list[str]) -> dict | None:
        raise NotImplementedError
