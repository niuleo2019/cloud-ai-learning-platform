from app.domain.repositories.word_repository import WordRepository
from app.interfaces.exceptions import AppException


class WordService:
    """应用服务：处理当前用户的单词增删改查。"""

    def __init__(self, word_repository: WordRepository):
        self.word_repository = word_repository

    def list_words(self, user_id: int) -> list[dict]:
        return self.word_repository.list_by_user(user_id)

    def create_word(self, user_id: int, payload: dict) -> dict:
        return self.word_repository.create_with_initial_review(user_id, payload)

    def update_word(self, user_id: int, word_id: int, payload: dict) -> dict:
        existing_word = self.word_repository.find_by_id_and_user(word_id, user_id)
        if not existing_word:
            raise AppException(code=40410, message="Word not found", status_code=404)
        return self.word_repository.update(word_id, user_id, payload)

    def delete_word(self, user_id: int, word_id: int) -> dict:
        deleted = self.word_repository.delete(word_id, user_id)
        if not deleted:
            raise AppException(code=40410, message="Word not found", status_code=404)
        return {"id": word_id}
