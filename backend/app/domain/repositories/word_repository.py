from abc import ABC, abstractmethod


class WordRepository(ABC):
    @abstractmethod
    def list_by_user(self, user_id: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def find_by_id_and_user(self, word_id: int, user_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def create_with_initial_review(self, user_id: int, payload: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def update(self, word_id: int, user_id: int, payload: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def delete(self, word_id: int, user_id: int) -> bool:
        raise NotImplementedError
