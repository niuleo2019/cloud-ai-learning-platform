from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.database import get_connection


class MySQLUserRepository(UserRepository):
    def find_by_email(self, email: str) -> dict | None:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, username, email, password_hash, created_at FROM users WHERE email = %s LIMIT 1",
                    (email,),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    def find_by_id(self, user_id: int) -> dict | None:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, username, email, created_at FROM users WHERE id = %s LIMIT 1",
                    (user_id,),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    def create(self, username: str, email: str, password_hash: str) -> dict:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (username, email, password_hash),
                )
                connection.commit()
                user_id = cursor.lastrowid
            return self.find_by_id(user_id)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
