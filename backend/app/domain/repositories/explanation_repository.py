from abc import ABC, abstractmethod


class ExplanationRepository(ABC):
    @abstractmethod
    def find_by_word(self, word: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, payload: dict) -> dict:
        """Insert, or replace the explanation already stored for this word."""
        raise NotImplementedError
