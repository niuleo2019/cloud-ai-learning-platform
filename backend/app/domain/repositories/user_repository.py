from abc import ABC, abstractmethod


class UserRepository(ABC):
    @abstractmethod
    def find_by_email(self, email: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, user_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, username: str, email: str, password_hash: str) -> dict:
        raise NotImplementedError
