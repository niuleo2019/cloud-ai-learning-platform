from fastapi import Request
from fastapi.responses import JSONResponse

from app.interfaces.exceptions import AppException


def success_response(data=None, message: str = ""):
    return {
        "success": True,
        "code": 0,
        "data": data if data is not None else {},
        "message": message,
    }


def error_response(message: str, status_code: int = 400, data=None, code: int | None = None):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "code": code if code is not None else status_code * 100,
            "data": data,
            "message": message,
        },
    )


async def app_exception_handler(request: Request, exc: AppException):
    return error_response(exc.message, exc.status_code, exc.data, exc.code)


async def http_exception_handler(request: Request, exc):
    return error_response(exc.detail, exc.status_code)


async def validation_exception_handler(request: Request, exc):
    return error_response("Request validation failed", 422, exc.errors(), 42200)
