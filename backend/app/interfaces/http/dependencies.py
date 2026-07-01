from fastapi import Depends, Header

from app.application.services.auth_service import AuthService
from app.application.services.review_service import ReviewService
from app.application.services.word_service import WordService
from app.domain.services.review_policy import ReviewPolicy
from app.infrastructure.repositories.mysql_review_repository import MySQLReviewRepository
from app.infrastructure.repositories.mysql_user_repository import MySQLUserRepository
from app.infrastructure.repositories.mysql_word_repository import MySQLWordRepository
from app.infrastructure.security.jwt_service import JwtService
from app.infrastructure.security.password_hasher import PasswordHasher
from app.interfaces.exceptions import AppException


def get_auth_service() -> AuthService:
    return AuthService(MySQLUserRepository(), PasswordHasher(), JwtService())


def get_word_service() -> WordService:
    return WordService(MySQLWordRepository())


def get_review_service() -> ReviewService:
    return ReviewService(MySQLReviewRepository(), ReviewPolicy())


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppException(code=40102, message="Missing token", status_code=401)

    token = authorization.replace("Bearer ", "", 1)

    try:
        return JwtService().verify_token(token)
    except ValueError as error:
        raise AppException(code=40103, message=str(error), status_code=401) from error
