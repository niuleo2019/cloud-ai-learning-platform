from datetime import datetime

from app.domain.repositories.review_repository import ReviewRepository
from app.infrastructure.database import get_connection


class MySQLReviewRepository(ReviewRepository):
    def list_due_today(self, user_id: int) -> list[dict]:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT w.id, w.word, w.meaning, w.example, w.source,
                           r.review_stage, r.last_review_at, r.next_review_at, r.remember_level
                    FROM review_records r
                    INNER JOIN words w ON w.id = r.word_id
                    WHERE r.user_id = %s AND r.next_review_at <= NOW()
                    ORDER BY r.next_review_at ASC
                    """,
                    (user_id,),
                )
                return cursor.fetchall()
        finally:
            connection.close()

    def find_by_word_id(self, user_id: int, word_id: int) -> dict | None:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM review_records WHERE user_id = %s AND word_id = %s LIMIT 1",
                    (user_id, word_id),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    def update_review(
        self,
        user_id: int,
        word_id: int,
        review_stage: int,
        next_review_at: datetime,
        remember_level: str,
    ) -> dict:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE review_records
                    SET review_stage = %s,
                        last_review_at = NOW(),
                        next_review_at = %s,
                        remember_level = %s
                    WHERE user_id = %s AND word_id = %s
                    """,
                    (review_stage, next_review_at, remember_level, user_id, word_id),
                )
                connection.commit()
            return self.find_by_word_id(user_id, word_id)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
