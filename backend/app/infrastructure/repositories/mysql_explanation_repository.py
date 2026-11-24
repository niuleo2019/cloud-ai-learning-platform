from app.domain.repositories.explanation_repository import ExplanationRepository
from app.infrastructure.database import get_connection


class MySQLExplanationRepository(ExplanationRepository):
    def find_by_word(self, word: str) -> dict | None:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT word, content, model, truncated, created_at, updated_at FROM word_explanations WHERE word = %s LIMIT 1",
                    (word,),
                )
                row = cursor.fetchone()
                if row:
                    row["truncated"] = bool(row["truncated"])
                return row
        finally:
            connection.close()

    def save(self, payload: dict) -> dict:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO word_explanations
                      (word, content, model, truncated, input_tokens, output_tokens, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      content = VALUES(content), model = VALUES(model), truncated = VALUES(truncated),
                      input_tokens = VALUES(input_tokens), output_tokens = VALUES(output_tokens),
                      created_by = VALUES(created_by)
                    """,
                    (
                        payload["word"],
                        payload["content"],
                        payload.get("model"),
                        1 if payload.get("truncated") else 0,
                        payload.get("input_tokens"),
                        payload.get("output_tokens"),
                        payload.get("created_by"),
                    ),
                )
                connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return self.find_by_word(payload["word"])
