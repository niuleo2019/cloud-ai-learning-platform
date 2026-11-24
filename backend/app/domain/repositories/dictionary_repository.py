from abc import ABC, abstractmethod


class DictionaryRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[dict]:
        """All imported dictionaries, in display order."""
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, dictionary_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, payload: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def update(self, dictionary_id: int, fields: dict) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def set_order(self, ordered_ids: list[int]) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, dictionary_id: int) -> bool:
        raise NotImplementedError
