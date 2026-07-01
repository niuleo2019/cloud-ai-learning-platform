import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("密码需包含至少一个字母")
        if not re.search(r"\d", v):
            raise ValueError("密码需包含至少一个数字")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class WordRequest(BaseModel):
    word: str = Field(min_length=1, max_length=120)
    meaning: str = Field(min_length=1)
    example: str | None = ""
    source: str | None = ""


class ReviewSubmitRequest(BaseModel):
    rememberLevel: str
