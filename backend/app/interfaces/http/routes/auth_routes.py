from fastapi import APIRouter, Depends

from app.application.schemas import LoginRequest, RegisterRequest
from app.application.services.auth_service import AuthService
from app.interfaces.http.dependencies import get_auth_service, get_current_user
from app.interfaces.http.response import success_response

router = APIRouter()


@router.post("/register")
def register(payload: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    result = auth_service.register(payload.username, payload.email, payload.password)
    return success_response(result, "Register successfully")


@router.post("/login")
def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    result = auth_service.login(payload.email, payload.password)
    return success_response(result, "Login successfully")


@router.get("/me")
def me(
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    user = auth_service.get_me(current_user["id"])
    return success_response(user, "Current user")
