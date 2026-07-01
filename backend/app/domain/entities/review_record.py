from dataclasses import dataclass
from datetime import datetime


@dataclass
class ReviewRecord:
    id: int
    user_id: int
    word_id: int
    review_stage: int
    last_review_at: datetime | None
    next_review_at: datetime
    remember_level: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
