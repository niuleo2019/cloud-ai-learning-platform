from dataclasses import dataclass
from datetime import datetime


@dataclass
class Word:
    id: int
    user_id: int
    word: str
    meaning: str
    example: str | None = None
    source: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
