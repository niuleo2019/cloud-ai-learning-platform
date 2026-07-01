from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.infrastructure.config.settings import settings


class JwtService:
    def create_token(self, user: dict) -> str:
        payload = {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "exp": datetime.now(timezone.utc) + self._parse_expires_in(settings.jwt_expires_in),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

    def verify_token(self, token: str) -> dict:
        try:
            return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        except JWTError as error:
            raise ValueError("Invalid or expired token") from error

    def _parse_expires_in(self, value: str) -> timedelta:
        if value.endswith("d"):
            return timedelta(days=int(value[:-1]))
        if value.endswith("h"):
            return timedelta(hours=int(value[:-1]))
        if value.endswith("m"):
            return timedelta(minutes=int(value[:-1]))
        return timedelta(days=7)
