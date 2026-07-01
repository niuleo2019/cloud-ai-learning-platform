from app.domain.repositories.word_repository import WordRepository
from app.infrastructure.database import get_connection


class MySQLWordRepository(WordRepository):
    def list_by_user(self, user_id: int) -> list[dict]:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT w.id, w.word, w.meaning, w.example, w.source, w.created_at, w.updated_at,
                           r.review_stage, r.next_review_at, r.remember_level
                    FROM words w
                    LEFT JOIN review_records r ON r.word_id = w.id
                    WHERE w.user_id = %s
                    ORDER BY w.created_at DESC
                    """,
                    (user_id,),
                )
                return cursor.fetchall()
        finally:
            connection.close()

    def find_by_id_and_user(self, word_id: int, user_id: int) -> dict | None:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM words WHERE id = %s AND user_id = %s LIMIT 1",
                    (word_id, user_id),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    def create_with_initial_review(self, user_id: int, payload: dict) -> dict:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO words (user_id, word, meaning, example, source)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        payload["word"],
                        payload["meaning"],
                        payload.get("example") or "",
                        payload.get("source") or "",
                    ),
                )
                word_id = cursor.lastrowid

                cursor.execute(
                    """
                    INSERT INTO review_records
                    (user_id, word_id, review_stage, last_review_at, next_review_at, remember_level)
                    VALUES (%s, %s, 0, NULL, NOW(), NULL)
                    """,
                    (user_id, word_id),
                )

                connection.commit()
            return self.find_by_id_and_user(word_id, user_id)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def update(self, word_id: int, user_id: int, payload: dict) -> dict:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE words
                    SET word = %s, meaning = %s, example = %s, source = %s
                    WHERE id = %s AND user_id = %s
                    """,
                    (
                        payload["word"],
                        payload["meaning"],
                        payload.get("example") or "",
                        payload.get("source") or "",
                        word_id,
                        user_id,
                    ),
                )
                connection.commit()
            return self.find_by_id_and_user(word_id, user_id)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def delete(self, word_id: int, user_id: int) -> bool:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM words WHERE id = %s AND user_id = %s", (word_id, user_id))
                connection.commit()
                return cursor.rowcount > 0
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
