"""Study-planning agent: reads the learner's vocabulary, reviews and listening mistakes, then writes today's plan.

Same tool-calling loop as the chat assistant (model decides -> code executes -> results go back),
but it ends by calling `save_study_plan`, whose input is validated before anything is stored.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date
from typing import Any

from app.application.services.agent_service import LlmClient
from app.application.services.review_service import ReviewService
from app.application.services.word_service import WordService
from app.domain.repositories.listening_repository import ListeningRepository
from app.domain.repositories.planner_repository import PracticeRepository, StudyPlanRepository
from app.domain.services.practice_analysis import summarise_attempts
from app.interfaces.exceptions import AppException

MAX_LOOP_ITERATIONS = 8
MAX_TASKS = 8
TASK_TYPES = ("review", "dictation", "retell", "vocabulary")

SYSTEM_PROMPT = """You are the study-planning coach inside an IELTS vocabulary and listening app. \
The learner is a Chinese-speaking adult in Australia aiming for IELTS listening band 8.

Make today's plan from the learner's real data:
1. Call get_learning_snapshot, get_listening_mistakes and get_due_reviews first. Base every task on what they return; \
never invent words, sentences or scores.
2. Prioritise: overdue / due reviews, then the weakest listening sentences (low scores, repeated mistakes), \
then repeatedly missed or misheard words (spelling, weak forms, linking, numbers).
3. Fit the plan into the minutes the learner has. 3-6 concrete tasks; each task says exactly what to do and why.
4. Task types: "review" (spaced review of due words), "dictation" or "retell" (one listening sentence: \
use its material_id and sentence_index from get_listening_mistakes), "vocabulary" (study or save the listed words).
5. If there is little data, say so and give a starter plan (e.g. import a listening section, do 5 dictation sentences).
6. Finish by calling save_study_plan exactly once. Write summary, titles and details in simple Chinese, \
keeping English words and sentences in English.
After saving, reply with one short sentence."""

TOOLS: list[dict] = [
    {
        "name": "get_learning_snapshot",
        "description": "Overview of the learner: library size, words due today, review stages, "
        "listening attempts and average scores over the last 7 days.",
        "strict": True,
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
    {
        "name": "get_listening_mistakes",
        "description": "Listening weaknesses over the last N days: most missed words, most misheard words "
        "(expected vs what the learner wrote or said) and the weakest sentences with material_id and sentence_index.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "How many days back to look, 1-30"}},
            "required": ["days"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_due_reviews",
        "description": "Words due for spaced review today (word, meaning, stage).",
        "strict": True,
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
    {
        "name": "save_study_plan",
        "description": "Save today's plan. Call once, at the end. material_id and sentence_index are -1 "
        "unless the task is a dictation or retell of a specific sentence.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "2-4 sentences: what the data shows and today's focus"},
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": list(TASK_TYPES)},
                            "title": {"type": "string"},
                            "detail": {"type": "string", "description": "Exactly what to do and why"},
                            "minutes": {"type": "integer"},
                            "material_id": {"type": "integer"},
                            "sentence_index": {"type": "integer"},
                            "words": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["type", "title", "detail", "minutes", "material_id", "sentence_index", "words"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["summary", "tasks"],
            "additionalProperties": False,
        },
    },
]


class PlannerTools:
    """Tool implementations bound to one learner (the id comes from the login token, never from the model)."""

    def __init__(
        self,
        user_id: int,
        plan_date: date,
        word_service: WordService,
        review_service: ReviewService,
        practice: PracticeRepository,
        plans: StudyPlanRepository,
        listening: ListeningRepository,
        model_name: str | None = None,
    ):
        self.user_id = user_id
        self.plan_date = plan_date
        self.word_service = word_service
        self.review_service = review_service
        self.practice = practice
        self.plans = plans
        self.listening = listening
        self.model_name = model_name
        self.saved_plan: dict | None = None

    def execute(self, name: str, tool_input: dict) -> dict:
        handler = {
            "get_learning_snapshot": self.get_learning_snapshot,
            "get_listening_mistakes": self.get_listening_mistakes,
            "get_due_reviews": self.get_due_reviews,
            "save_study_plan": self.save_study_plan,
        }.get(name)
        if handler is None:
            raise PlanError(f"Unknown tool: {name}")
        return handler(**tool_input)

    def get_learning_snapshot(self) -> dict:
        words = self.word_service.list_words(self.user_id)
        due = self.review_service.list_today_reviews(self.user_id)
        stages = Counter(str(w.get("review_stage") if w.get("review_stage") is not None else "new") for w in words)
        week = summarise_attempts(self.practice.recent(self.user_id, 7))
        return {
            "date": str(self.plan_date),
            "library_words": len(words),
            "due_today": len(due),
            "review_stages": dict(stages),
            "listening_last_7_days": {"attempts": week["attempt_count"], "average_score": week["average_score"]},
        }

    def get_listening_mistakes(self, days: int) -> dict:
        days = max(1, min(int(days), 30))
        return summarise_attempts(self.practice.recent(self.user_id, days))

    def get_due_reviews(self) -> dict:
        due = self.review_service.list_today_reviews(self.user_id)
        return {
            "count": len(due),
            "words": [
                {"word": r.get("word"), "meaning": (r.get("meaning") or "")[:120], "stage": r.get("review_stage")}
                for r in due[:30]
            ],
        }

    def save_study_plan(self, summary: str, tasks: list[dict]) -> dict:
        summary = (summary or "").strip()
        if not summary:
            raise PlanError("summary is empty")
        if not tasks or len(tasks) > MAX_TASKS:
            raise PlanError(f"give between 1 and {MAX_TASKS} tasks")
        clean: list[dict] = []
        for position, task in enumerate(tasks, start=1):
            kind = task.get("type")
            if kind not in TASK_TYPES:
                raise PlanError(f"task {position}: unknown type {kind!r}")
            item = {
                "id": f"t{position}",
                "type": kind,
                "title": str(task.get("title", "")).strip()[:80] or kind,
                "detail": str(task.get("detail", "")).strip()[:400],
                "minutes": max(1, min(int(task.get("minutes") or 5), 60)),
                "material_id": None,
                "sentence_index": None,
                "words": [str(w).strip()[:40] for w in (task.get("words") or []) if str(w).strip()][:12],
            }
            if kind in ("dictation", "retell"):
                material_id, index = int(task.get("material_id", -1)), int(task.get("sentence_index", -1))
                material = self.listening.find_by_id_and_user(material_id, self.user_id) if material_id > 0 else None
                sentences = (material or {}).get("sentences") or []
                if not material or not 0 <= index < len(sentences):
                    raise PlanError(
                        f"task {position}: material_id/sentence_index must come from get_listening_mistakes"
                    )
                item["material_id"], item["sentence_index"] = material_id, index
            clean.append(item)
        self.saved_plan = self.plans.save(self.user_id, self.plan_date, summary[:1200], clean, self.model_name)
        return {"saved": True, "tasks": len(clean)}


class PlanError(Exception):
    """A tool input the model can fix; returned to it as an error tool_result."""


class PlannerService:
    def __init__(self, llm: LlmClient, tools: PlannerTools):
        self.llm = llm
        self.tools = tools

    def make_plan(self, minutes: int, focus: str) -> dict:
        request = f"I have {minutes} minutes today."
        if focus.strip():
            request += f" I want to focus on: {focus.strip()}"
        messages: list[dict] = [{"role": "user", "content": request}]
        tool_calls: list[dict] = []
        usage = {"input_tokens": 0, "output_tokens": 0}

        for _ in range(MAX_LOOP_ITERATIONS):
            response = self.llm.create(system=SYSTEM_PROMPT, tools=TOOLS, messages=messages)
            for key in usage:
                usage[key] += getattr(getattr(response, "usage", None), key, 0) or 0
            if response.stop_reason == "refusal":
                raise AppException(42251, "The AI declined to make a plan", 422)
            if response.stop_reason in ("tool_use", "pause_turn"):
                messages.append({"role": "assistant", "content": response.content})
                if response.stop_reason == "tool_use":
                    results = [self._run(block, tool_calls) for block in response.content if block.type == "tool_use"]
                    messages.append({"role": "user", "content": results})
                continue
            break
        else:
            raise AppException(50821, "The planner took too many steps. Please try again.", 508)

        if self.tools.saved_plan is None:
            raise AppException(50251, "The planner finished without saving a plan. Please try again.", 502)
        return {"plan": self.tools.saved_plan, "tool_calls": tool_calls, "usage": usage}

    def _run(self, block: Any, tool_calls: list[dict]) -> dict:
        tool_input = block.input if isinstance(block.input, dict) else {}
        try:
            output = self.tools.execute(block.name, tool_input)
            tool_calls.append({"name": block.name, "ok": True})
            return {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(output, ensure_ascii=False, default=str)}
        except (PlanError, AppException, TypeError, ValueError) as error:
            message = getattr(error, "message", None) or str(error)
            tool_calls.append({"name": block.name, "ok": False, "error": message})
            return {"type": "tool_result", "tool_use_id": block.id, "content": f"Error: {message}", "is_error": True}
