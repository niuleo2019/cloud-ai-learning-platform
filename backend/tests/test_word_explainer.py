"""Deep word explanations: caching, validation and AI failure handling (fake model, no API cost)."""
import pytest

from app.application.services.word_explainer_service import SYSTEM_PROMPT, WordExplainerService, normalise_word
from app.interfaces.exceptions import AppException


class FakeRepository:
    def __init__(self):
        self.rows = {}

    def find_by_word(self, word):
        return dict(self.rows[word]) if word in self.rows else None

    def save(self, payload):
        self.rows[payload["word"]] = {k: payload.get(k) for k in ("word", "content", "model", "truncated")}
        return dict(self.rows[payload["word"]])


class FakeModel:
    calls = []

    def __init__(self, text="## 一、核心体验\n...", stop_reason="end_turn"):
        self.text, self.stop_reason = text, stop_reason

    def generate_text(self, *, system, prompt, max_tokens=16000):
        FakeModel.calls.append(prompt)
        return {"text": self.text, "stop_reason": self.stop_reason, "model": "fake", "usage": {"input_tokens": 1, "output_tokens": 2}}


def make(model=None):
    FakeModel.calls = []
    return WordExplainerService(FakeRepository(), model_factory=lambda: model or FakeModel())


def test_prompt_contains_the_learners_method_and_honesty_rules():
    assert "逐字母形状分析" in SYSTEM_PROMPT and "把字母连成一部电影" in SYSTEM_PROMPT
    assert "严禁" in SYSTEM_PROMPT and "尚未接入刘一男讲义" in SYSTEM_PROMPT


def test_generates_once_then_serves_from_cache():
    service = make()
    first = service.generate("  Cemetery ", user_id=7)
    second = service.generate("cemetery", user_id=7)
    assert first["cached"] is False and second["cached"] is True
    assert FakeModel.calls == ["cemetery"]  # normalised, and the AI is called only once
    assert service.get_cached("CEMETERY")["content"].startswith("## 一")


def test_regenerate_calls_the_model_again():
    service = make()
    service.generate("impulse", user_id=7)
    service.generate("impulse", user_id=7, regenerate=True)
    assert FakeModel.calls == ["impulse", "impulse"]


def test_cached_read_never_builds_the_model():
    def no_model():
        raise AssertionError("must not create an AI client for a cached read")

    service = WordExplainerService(FakeRepository(), model_factory=no_model)
    assert service.get_cached("sprinkle") is None


@pytest.mark.parametrize("bad", ["", "hello world and more words that go on and on and on", "<script>", "12345", "a/b"])
def test_rejects_non_words(bad):
    with pytest.raises(AppException):
        normalise_word(bad)


def test_refusal_and_empty_answers_are_errors_and_not_cached():
    service = make(FakeModel(stop_reason="refusal", text=""))
    with pytest.raises(AppException):
        service.generate("affiliate", user_id=7)
    assert service.get_cached("affiliate") is None

    service = make(FakeModel(text="   "))
    with pytest.raises(AppException):
        service.generate("affiliate", user_id=7)


def test_truncated_answer_is_kept_but_flagged():
    service = make(FakeModel(stop_reason="max_tokens"))
    assert service.generate("procure", user_id=7)["truncated"] is True
