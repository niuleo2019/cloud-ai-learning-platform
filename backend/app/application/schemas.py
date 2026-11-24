import re
from datetime import date as date_type

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


class ChatTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=4000)


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class SentenceUpdateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class DictionaryUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    enabled: bool | None = None


class DictionaryOrderRequest(BaseModel):
    ids: list[int] = Field(max_length=200)


class WrongWord(BaseModel):
    expected: str = Field(max_length=60)
    actual: str = Field(max_length=60)


class PracticeAttemptRequest(BaseModel):
    material_id: int = Field(gt=0)
    sentence_index: int = Field(ge=0)
    mode: str = Field(pattern="^(dictation|retell)$")
    score: int = Field(ge=0, le=100)
    expected_text: str = Field(min_length=1, max_length=1000)
    attempt_text: str = Field(default="", max_length=1000)
    missed: list[str] = Field(default_factory=list, max_length=60)
    wrong: list[WrongWord] = Field(default_factory=list, max_length=60)


class StudyPlanRequest(BaseModel):
    date: date_type
    minutes: int = Field(default=30, ge=5, le=180)
    focus: str = Field(default="", max_length=200)


class StudyPlanDoneRequest(BaseModel):
    date: date_type
    done: list[str] = Field(default_factory=list, max_length=20)
