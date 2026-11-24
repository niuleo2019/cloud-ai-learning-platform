import json

from app.domain.repositories.dictionary_repository import DictionaryRepository
from app.infrastructure.database import get_connection

_UPDATABLE = {"title", "enabled", "sort_order"}


def _clean(row: dict | None) -> dict | None:
    if row is None:
        return None
    if isinstance(row.get("mdd_files"), (str, bytes)):
        row["mdd_files"] = json.loads(row["mdd_files"])
    row["mdd_files"] = row.get("mdd_files") or []
    row["enabled"] = bool(row.get("enabled"))
    return row


class MySQLDictionaryRepository(DictionaryRepository):
    def _write(self, sql: str, params: tuple) -> tuple[int, int]:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                connection.commit()
                return cursor.rowcount, cursor.lastrowid
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_all(self) -> list[dict]:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM dictionaries ORDER BY sort_order ASC, id ASC")
                return [_clean(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    def find_by_id(self, dictionary_id: int) -> dict | None:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM dictionaries WHERE id = %s LIMIT 1", (dictionary_id,))
                return _clean(cursor.fetchone())
        finally:
            connection.close()

    def create(self, payload: dict) -> dict:
        _rows, new_id = self._write(
            """
            INSERT INTO dictionaries (title, folder, mdx_file, mdd_files, entry_count, enabled, sort_order, uploaded_by)
            VALUES (%s, %s, %s, %s, %s, 1,
                    (SELECT next_order FROM (SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order FROM dictionaries) AS t),
                    %s)
            """,
            (
                payload["title"],
                payload["folder"],
                payload["mdx_file"],
                json.dumps(payload.get("mdd_files") or [], ensure_ascii=False),
                payload.get("entry_count", 0),
                payload.get("uploaded_by"),
            ),
        )
        return self.find_by_id(new_id)

    def update(self, dictionary_id: int, fields: dict) -> dict | None:
        fields = {key: value for key, value in fields.items() if key in _UPDATABLE}
        if fields:
            assignments = ", ".join(f"{key} = %s" for key in fields)
            self._write(f"UPDATE dictionaries SET {assignments} WHERE id = %s", (*fields.values(), dictionary_id))
        return self.find_by_id(dictionary_id)

    def set_order(self, ordered_ids: list[int]) -> None:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                for position, dictionary_id in enumerate(ordered_ids, start=1):
                    cursor.execute("UPDATE dictionaries SET sort_order = %s WHERE id = %s", (position, dictionary_id))
                connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def delete(self, dictionary_id: int) -> bool:
        rows, _ = self._write("DELETE FROM dictionaries WHERE id = %s", (dictionary_id,))
        return rows > 0
