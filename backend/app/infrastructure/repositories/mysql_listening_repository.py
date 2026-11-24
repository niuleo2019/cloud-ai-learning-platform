import json

from app.domain.repositories.listening_repository import ListeningRepository
from app.infrastructure.database import get_connection

_SUMMARY_COLUMNS = """
    id, title, original_filename, status, error_message, duration_seconds,
    JSON_LENGTH(sentences) AS sentence_count, created_at, updated_at
"""


def _clean(row: dict | None) -> dict | None:
    if row is None:
        return None
    if row.get("duration_seconds") is not None:
        row["duration_seconds"] = float(row["duration_seconds"])
    if isinstance(row.get("sentences"), (str, bytes)):
        row["sentences"] = json.loads(row["sentences"])
    return row


class MySQLListeningRepository(ListeningRepository):
    def _execute(self, sql: str, params: tuple) -> int:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                connection.commit()
                return cursor.rowcount
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def create(self, user_id: int, title: str, audio_file: str, original_filename: str) -> dict:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO listening_materials (user_id, title, audio_file, original_filename, status)
                    VALUES (%s, %s, %s, %s, 'processing')
                    """,
                    (user_id, title, audio_file, original_filename),
                )
                material_id = cursor.lastrowid
                connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return self.find_by_id_and_user(material_id, user_id)

    def list_by_user(self, user_id: int) -> list[dict]:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT {_SUMMARY_COLUMNS} FROM listening_materials WHERE user_id = %s ORDER BY created_at DESC, id DESC",
                    (user_id,),
                )
                return [_clean(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    def find_by_id_and_user(self, material_id: int, user_id: int) -> dict | None:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM listening_materials WHERE id = %s AND user_id = %s LIMIT 1",
                    (material_id, user_id),
                )
                return _clean(cursor.fetchone())
        finally:
            connection.close()

    def mark_ready(self, material_id: int, duration: float, sentences: list[dict]) -> None:
        self._execute(
            """
            UPDATE listening_materials
            SET status = 'ready', error_message = NULL, duration_seconds = %s, sentences = %s
            WHERE id = %s
            """,
            (duration, json.dumps(sentences, ensure_ascii=False), material_id),
        )

    def update_sentences(self, material_id: int, user_id: int, sentences: list[dict]) -> None:
        self._execute(
            "UPDATE listening_materials SET sentences = %s WHERE id = %s AND user_id = %s",
            (json.dumps(sentences, ensure_ascii=False), material_id, user_id),
        )

    def mark_failed(self, material_id: int, error_message: str) -> None:
        self._execute(
            "UPDATE listening_materials SET status = 'failed', error_message = %s WHERE id = %s",
            (error_message[:500], material_id),
        )

    def delete(self, material_id: int, user_id: int) -> bool:
        return self._execute(
            "DELETE FROM listening_materials WHERE id = %s AND user_id = %s",
            (material_id, user_id),
        ) > 0
