"""Study-planning agent: mistake analysis, the tool loop and plan validation (fake model, no API cost)."""
from datetime import date
from types import SimpleNamespace

import pytest

from app.application.services.planner_service import PlannerService, PlannerTools
from app.domain.services.practice_analysis import summarise_attempts
from app.interfaces.exceptions import AppException

ATTEMPTS = [
    {"material_id": 2, "title": "IELTS 13", "sentence_index": 10, "mode": "dictation", "score": 86,
     "expected_text": "We're not talking about gradual evolution here.", "missed": [],
     "wrong": [{"expected": "evolution", "actual": "revolution"}]},
    {"material_id": 2, "title": "IELTS 13", "sentence_index": 10, "mode": "retell", "score": 100,
     "expected_text": "We're not talking about gradual evolution here.", "missed": [], "wrong": []},
    {"material_id": 2, "title": "IELTS 13", "sentence_index": 4, "mode": "dictation", "score": 50,
     "expected_text": "The court costs $15 per hour.", "missed": ["costs", "per"], "wrong": []},
    {"material_id": 2, "title": "IELTS 13", "sentence_index": 4, "mode": "dictation", "score": 70,
     "expected_text": "The court costs $15 per hour.", "missed": ["costs"], "wrong": []},
]


def test_summary_finds_missed_words_and_weakest_sentences():
    summary = summarise_attempts(ATTEMPTS)
    assert summary["attempt_count"] == 4
    assert summary["most_missed_words"][0] == {"word": "costs", "times": 2, "example": "The court costs $15 per hour."}
    assert summary["most_misheard_words"][0]["word"] == 'evolution (heard as "revolution")'
    # sentence 10 reached 100, so only sentence 4 (best 70) is weak
    assert [(s["sentence_index"], s["best_score"], s["attempts"]) for s in summary["weakest_sentences"]] == [(4, 70, 2)]
    assert summary["average_score"] == {"dictation": 69, "retell": 100}


class FakePractice:
    def recent(self, user_id, days):
        return ATTEMPTS


class FakePlans:
    def __init__(self):
        self.saved = None

    def save(self, user_id, plan_date, summary, tasks, model):
        self.saved = {"user_id": user_id, "plan_date": str(plan_date), "summary": summary, "tasks": tasks, "done": []}
        return self.saved


class FakeListening:
    def find_by_id_and_user(self, material_id, user_id):
        if material_id == 2 and user_id == 7:
            return {"id": 2, "sentences": [{"text": f"s{i}"} for i in range(40)]}
        return None


class FakeWords:
    def list_words(self, user_id):
        return [{"word": "evidence", "review_stage": 1}, {"word": "gorgeous", "review_stage": 1}, {"word": "new", "review_stage": None}]


class FakeReviews:
    def list_today_reviews(self, user_id):
        return [{"word": "evidence", "meaning": "证据", "review_stage": 1}]


def tool_use(block_id, name, tool_input):
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=tool_input)


def response(stop_reason, *content):
    return SimpleNamespace(stop_reason=stop_reason, content=list(content), usage=SimpleNamespace(input_tokens=5, output_tokens=3))


class FakeLlm:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, *, system, tools, messages):
        self.requests.append([dict(m) for m in messages])
        return self.responses.pop(0)


def make(llm, user_id=7):
    plans = FakePlans()
    tools = PlannerTools(user_id, date(2026, 11, 22), FakeWords(), FakeReviews(), FakePractice(), plans, FakeListening(), "fake")
    return PlannerService(llm, tools), plans


GOOD_PLAN = {
    "summary": "你常把 evolution 听成 revolution；先复习到期单词，再精听第 5 句。",
    "tasks": [
        {"type": "review", "title": "复习 1 个到期单词", "detail": "evidence", "minutes": 5, "material_id": -1, "sentence_index": -1, "words": ["evidence"]},
        {"type": "dictation", "title": "重听第 5 句", "detail": "注意 costs 的尾音", "minutes": 10, "material_id": 2, "sentence_index": 4, "words": ["costs"]},
    ],
}


def test_agent_reads_data_then_saves_a_validated_plan():
    llm = FakeLlm(
        response("tool_use", tool_use("a", "get_learning_snapshot", {}), tool_use("b", "get_listening_mistakes", {"days": 7}),
                 tool_use("c", "get_due_reviews", {})),
        response("tool_use", tool_use("d", "save_study_plan", GOOD_PLAN)),
        response("end_turn", SimpleNamespace(type="text", text="已为你生成今天的计划。")),
    )
    service, plans = make(llm)
    result = service.make_plan(30, "")

    assert [c["name"] for c in result["tool_calls"]] == ["get_learning_snapshot", "get_listening_mistakes", "get_due_reviews", "save_study_plan"]
    assert plans.saved["user_id"] == 7
    assert [t["id"] for t in plans.saved["tasks"]] == ["t1", "t2"]
    assert plans.saved["tasks"][0]["material_id"] is None
    assert plans.saved["tasks"][1]["sentence_index"] == 4
    snapshot = llm.requests[1][-1]["content"][0]["content"]
    assert '"due_today": 1' in snapshot and '"library_words": 3' in snapshot
    assert llm.requests[0][0]["content"] == "I have 30 minutes today."


def test_invented_sentence_is_rejected_and_the_model_can_fix_it():
    bad = {**GOOD_PLAN, "tasks": [{**GOOD_PLAN["tasks"][1], "material_id": 99}]}
    llm = FakeLlm(
        response("tool_use", tool_use("a", "save_study_plan", bad)),
        response("tool_use", tool_use("b", "save_study_plan", GOOD_PLAN)),
        response("end_turn", SimpleNamespace(type="text", text="ok")),
    )
    service, plans = make(llm)
    result = service.make_plan(20, "numbers")
    assert result["tool_calls"][0]["ok"] is False
    assert llm.requests[1][-1]["content"][0]["is_error"] is True
    assert len(plans.saved["tasks"]) == 2
    assert "focus on: numbers" in llm.requests[0][0]["content"]


def test_another_users_material_cannot_be_planned():
    llm = FakeLlm(response("tool_use", tool_use("a", "save_study_plan", GOOD_PLAN)), response("end_turn"))
    service, plans = make(llm, user_id=8)
    with pytest.raises(AppException):  # never saved -> error
        service.make_plan(30, "")
    assert plans.saved is None


def test_finishing_without_saving_is_an_error():
    service, _ = make(FakeLlm(response("end_turn", SimpleNamespace(type="text", text="Here is a plan..."))))
    with pytest.raises(AppException):
        service.make_plan(30, "")


def test_too_many_tasks_rejected():
    tools = make(FakeLlm())[0].tools
    task = GOOD_PLAN["tasks"][0]
    with pytest.raises(Exception):
        tools.save_study_plan("x", [task] * 9)
