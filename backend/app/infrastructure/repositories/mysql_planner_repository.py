import json
from datetime import date

from app.domain.repositories.planner_repository import PracticeRepository, StudyPlanRepository
from app.infrastructure.database import get_connection


def _execute(sql: str, params: tuple) -> None:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _query(sql: str, params: tuple) -> list[dict]:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        connection.close()


def _json(value, default):
    if isinstance(value, (str, bytes)):
        return json.loads(value)
    return value if value is not None else default


class MySQLPracticeRepository(PracticeRepository):
    def record(self, user_id: int, attempt: dict) -> None:
        _execute(
            """
            INSERT INTO practice_attempts
              (user_id, material_id, sentence_index, mode, score, expected_text, attempt_text, missed, wrong)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                attempt["material_id"],
                attempt["sentence_index"],
                attempt["mode"],
                attempt["score"],
                attempt["expected_text"][:1000],
                attempt["attempt_text"][:1000],
                json.dumps(attempt.get("missed") or [], ensure_ascii=False),
                json.dumps(attempt.get("wrong") or [], ensure_ascii=False),
            ),
        )

    def recent(self, user_id: int, days: int) -> list[dict]:
        rows = _query(
            """
            SELECT a.material_id, m.title, a.sentence_index, a.mode, a.score, a.expected_text,
                   a.missed, a.wrong, a.created_at
            FROM practice_attempts a
            JOIN listening_materials m ON m.id = a.material_id
            WHERE a.user_id = %s AND a.created_at >= NOW() - INTERVAL %s DAY
            ORDER BY a.created_at DESC
            LIMIT 500
            """,
            (user_id, days),
        )
        for row in rows:
            row["missed"] = _json(row.get("missed"), [])
            row["wrong"] = _json(row.get("wrong"), [])
        return rows


class MySQLStudyPlanRepository(StudyPlanRepository):
    def find(self, user_id: int, plan_date: date) -> dict | None:
        rows = _query(
            "SELECT plan_date, summary, tasks, done, model, updated_at FROM study_plans WHERE user_id = %s AND plan_date = %s",
            (user_id, plan_date),
        )
        if not rows:
            return None
        row = rows[0]
        row["tasks"] = _json(row.get("tasks"), [])
        row["done"] = _json(row.get("done"), [])
        row["plan_date"] = str(row["plan_date"])
        return row

    def save(self, user_id: int, plan_date: date, summary: str, tasks: list[dict], model: str | None) -> dict:
        _execute(
            """
            INSERT INTO study_plans (user_id, plan_date, summary, tasks, done, model)
            VALUES (%s, %s, %s, %s, '[]', %s)
            ON DUPLICATE KEY UPDATE summary = VALUES(summary), tasks = VALUES(tasks), done = '[]', model = VALUES(model)
            """,
            (user_id, plan_date, summary, json.dumps(tasks, ensure_ascii=False), model),
        )
        return self.find(user_id, plan_date)

    def set_done(self, user_id: int, plan_date: date, done: list[str]) -> dict | None:
        _execute(
            "UPDATE study_plans SET done = %s WHERE user_id = %s AND plan_date = %s",
            (json.dumps(done), user_id, plan_date),
        )
        return self.find(user_id, plan_date)
