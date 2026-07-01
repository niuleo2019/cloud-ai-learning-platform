from pathlib import Path
import sys

backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))

from app.infrastructure.repositories.mysql_user_repository import MySQLUserRepository
from app.infrastructure.security.password_hasher import PasswordHasher


def main():
    repository = MySQLUserRepository()
    hasher = PasswordHasher()

    email = "test@example.com"
    existing_user = repository.find_by_email(email)
    if existing_user:
        print("Test user already exists: test@example.com / 123456")
        return

    repository.create("Test User", email, hasher.hash("123456"))
    print("Test user created: test@example.com / 123456")


if __name__ == "__main__":
    main()
