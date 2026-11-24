"""Agent loop tests with a fake LLM client: no network, no API cost."""
from types import SimpleNamespace

import pytest

from app.application.services.agent_service import AgentService, AgentTools, _build_messages
from app.interfaces.exceptions import AppException


def text(value):
    return SimpleNamespace(type="text", text=value)


def tool_use(block_id, name, tool_input):
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=tool_input)


def response(stop_reason, *content):
    usage = SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0)
    return SimpleNamespace(stop_reason=stop_reason, content=list(content), usage=usage)


class FakeLlm:
    """Returns scripted responses and records every request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, *, system, tools, messages):
        self.requests.append([dict(m) for m in messages])
        return self.responses.pop(0)


class FakeWordService:
    def __init__(self, words=None):
        self.words = list(words or [])
        self.created = []

    def list_words(self, user_id):
        return [w for w in self.words if w["user_id"] == user_id]

    def create_word(self, user_id, payload):
        word = {"id": len(self.words) + 1, "user_id": user_id, **payload}
        self.words.append(word)
        self.created.append((user_id, payload))
        return word


class FakeReviewService:
    def list_today_reviews(self, user_id):
        return [{"id": 1, "word": "evidence", "meaning": "证据", "review_stage": 0, "next_review_at": "2026-11-21"}]


def make_agent(llm, words=None, user_id=7):
    word_service = FakeWordService(words)
    tools = AgentTools(
        user_id=user_id,
        word_service=word_service,
        review_service=FakeReviewService(),
        lookup_word=lambda w: {"found": True, "word": w, "definition": "the ability to keep something"},
    )
    return AgentService(llm, tools), word_service


def test_plain_answer_without_tools():
    agent, _ = make_agent(FakeLlm(response("end_turn", text("Hi!"))))
    result = agent.chat("hello", [])
    assert result["reply"] == "Hi!"
    assert result["tool_calls"] == []


def test_tool_loop_adds_word_for_the_authenticated_user():
    llm = FakeLlm(
        response("tool_use", tool_use("t1", "lookup_word", {"word": "Retention"})),
        response("tool_use", tool_use("t2", "add_word", {"word": "retention", "meaning": "keeping; 保持", "example": ""})),
        response("end_turn", text("Saved retention.")),
    )
    agent, words = make_agent(llm, user_id=7)

    result = agent.chat("save retention", [])

    assert result["reply"] == "Saved retention."
    assert [c["name"] for c in result["tool_calls"]] == ["lookup_word", "add_word"]
    assert words.created == [(7, {"word": "retention", "meaning": "keeping; 保持", "example": "", "source": "AI assistant"})]
    # The second request carries the assistant tool_use turn and the matching tool_result.
    second = llm.requests[1]
    assert second[-1]["role"] == "user"
    assert second[-1]["content"][0]["tool_use_id"] == "t1"


def test_duplicate_word_is_not_added_again():
    existing = [{"id": 1, "user_id": 7, "word": "evidence", "meaning": "证据"}]
    llm = FakeLlm(
        response("tool_use", tool_use("t1", "add_word", {"word": "Evidence", "meaning": "proof; 证据", "example": ""})),
        response("end_turn", text("Already saved.")),
    )
    agent, words = make_agent(llm, words=existing)

    agent.chat("add evidence", [])

    assert words.created == []
    assert '"already in library"' in llm.requests[1][-1]["content"][0]["content"]


def test_unknown_tool_returns_error_result_instead_of_crashing():
    llm = FakeLlm(
        response("tool_use", tool_use("t1", "delete_word", {"id": 1})),
        response("end_turn", text("I can't delete words.")),
    )
    agent, _ = make_agent(llm)

    result = agent.chat("delete evidence", [])

    tool_result = llm.requests[1][-1]["content"][0]
    assert tool_result["is_error"] is True
    assert result["tool_calls"][0]["ok"] is False


def test_parallel_tool_calls_answered_in_one_message():
    llm = FakeLlm(
        response(
            "tool_use",
            tool_use("a", "lookup_word", {"word": "memory"}),
            tool_use("b", "get_due_reviews", {}),
        ),
        response("end_turn", text("ok")),
    )
    agent, _ = make_agent(llm)
    agent.chat("hi", [])
    results = llm.requests[1][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"]


def test_loop_stops_after_max_iterations():
    llm = FakeLlm(*[response("tool_use", tool_use(f"t{i}", "get_due_reviews", {})) for i in range(20)])
    agent, _ = make_agent(llm)
    with pytest.raises(AppException):
        agent.chat("loop", [])


def test_refusal_returns_safe_message():
    agent, _ = make_agent(FakeLlm(response("refusal")))
    assert "can't help" in agent.chat("x", [])["reply"]


def test_history_is_normalised_to_alternating_turns():
    history = [
        {"role": "assistant", "content": "welcome"},  # dropped: must start with user
        {"role": "user", "content": "a"},
        {"role": "user", "content": "b"},  # merged with previous user turn
        {"role": "assistant", "content": "c"},
    ]
    messages = _build_messages(history, "d")
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[0]["content"] == "a\n\nb"
    assert messages[-1]["content"] == "d"
