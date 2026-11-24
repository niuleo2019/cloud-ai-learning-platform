from abc import ABC, abstractmethod


class ListeningRepository(ABC):
    @abstractmethod
    def create(self, user_id: int, title: str, audio_file: str, original_filename: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_by_user(self, user_id: int) -> list[dict]:
        """Materials without the sentence list (kept small for the list page)."""
        raise NotImplementedError

    @abstractmethod
    def find_by_id_and_user(self, material_id: int, user_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def mark_ready(self, material_id: int, duration: float, sentences: list[dict]) -> None:
        raise NotImplementedError

    @abstractmethod
    def update_sentences(self, material_id: int, user_id: int, sentences: list[dict]) -> None:
        raise NotImplementedError

    @abstractmethod
    def mark_failed(self, material_id: int, error_message: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, material_id: int, user_id: int) -> bool:
        raise NotImplementedError
