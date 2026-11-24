"""Deep word explanations: real etymology + letter-shape memory + continuous "movie" scene.

The teaching method lives in prompts/word_explanation_zh.md (the learner's own system).
Each word is generated once with Claude and cached, so repeat lookups are instant and free.
"""
from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Callable, Protocol

from app.domain.repositories.explanation_repository import ExplanationRepository
from app.interfaces.exceptions import AppException

SYSTEM_PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "word_explanation_zh.md").read_text(encoding="utf-8")
WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z'\- ]{0,38}[A-Za-z]|[A-Za-z]")
MAX_OUTPUT_TOKENS = 16000

# One generation per word at a time: a double tap must not pay twice.
_in_flight: dict[str, threading.Lock] = {}
_in_flight_guard = threading.Lock()


class TextModel(Protocol):
    def generate_text(self, *, system: str, prompt: str, max_tokens: int = ...) -> dict: ...


def normalise_word(word: str) -> str:
    clean = " ".join(word.strip().split())
    if not WORD_PATTERN.fullmatch(clean):
        raise AppException(40050, "Please enter a single English word", 400)
    return clean.lower()


class WordExplainerService:
    def __init__(self, repository: ExplanationRepository, model_factory: Callable[[], TextModel]):
        self.repository = repository
        # Created lazily: reading a cached explanation must work without an API key.
        self.model_factory = model_factory

    def get_cached(self, word: str) -> dict | None:
        return self.repository.find_by_word(normalise_word(word))

    def generate(self, word: str, user_id: int, regenerate: bool = False) -> dict:
        key = normalise_word(word)
        if not regenerate:
            cached = self.repository.find_by_word(key)
            if cached:
                return {**cached, "cached": True}

        with _in_flight_guard:
            lock = _in_flight.setdefault(key, threading.Lock())
        with lock:
            # Another request may have finished this word while we waited.
            if not regenerate:
                cached = self.repository.find_by_word(key)
                if cached:
                    return {**cached, "cached": True}

            result = self.model_factory().generate_text(system=SYSTEM_PROMPT, prompt=key, max_tokens=MAX_OUTPUT_TOKENS)
            if result["stop_reason"] == "refusal":
                raise AppException(42250, "The AI declined to explain this word", 422)
            content = result["text"].strip()
            if not content:
                raise AppException(50250, "The AI returned an empty explanation. Please try again.", 502)

            saved = self.repository.save(
                {
                    "word": key,
                    "content": content,
                    "model": result.get("model"),
                    "truncated": result["stop_reason"] == "max_tokens",
                    "input_tokens": result.get("usage", {}).get("input_tokens"),
                    "output_tokens": result.get("usage", {}).get("output_tokens"),
                    "created_by": user_id,
                }
            )
            return {**saved, "cached": False}
