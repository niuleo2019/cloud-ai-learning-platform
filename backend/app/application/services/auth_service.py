from app.domain.repositories.user_repository import UserRepository
from app.interfaces.exceptions import AppException
from app.infrastructure.security.jwt_service import JwtService
from app.infrastructure.security.password_hasher import PasswordHasher


class AuthService:
    """应用服务：编排注册、登录、获取当前用户这几个用例。"""

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        jwt_service: JwtService,
    ):
        self.user_repository = user_repository
        self.password_hasher = password_hasher
        self.jwt_service = jwt_service

    def register(self, username: str, email: str, password: str) -> dict:
        existing_user = self.user_repository.find_by_email(email)
        if existing_user:
            raise AppException(code=40901, message="Email already registered", status_code=409)

        password_hash = self.password_hasher.hash(password)
        user = self.user_repository.create(username, email, password_hash)
        token = self.jwt_service.create_token(user)

        return {"user": user, "token": token}

    def login(self, email: str, password: str) -> dict:
        user_with_password = self.user_repository.find_by_email(email)
        if not user_with_password:
            raise AppException(code=40101, message="Invalid email or password", status_code=401)

        if not self.password_hasher.verify(password, user_with_password["password_hash"]):
            raise AppException(code=40101, message="Invalid email or password", status_code=401)

        user = {
            "id": user_with_password["id"],
            "username": user_with_password["username"],
            "email": user_with_password["email"],
            "created_at": user_with_password["created_at"],
        }
        token = self.jwt_service.create_token(user)

        return {"user": user, "token": token}

    def get_me(self, user_id: int) -> dict:
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise AppException(code=40401, message="User not found", status_code=404)
        return user
