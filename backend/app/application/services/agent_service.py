import json
from typing import Any, Callable, Protocol

from app.application.services.review_service import ReviewService
from app.application.services.word_service import WordService
from app.interfaces.exceptions import AppException

MAX_LOOP_ITERATIONS = 8
MAX_WORDS_ADDED_PER_REQUEST = 10

SYSTEM_PROMPT = """You are the learning assistant inside a mobile vocabulary app. \
Users are Chinese-speaking adults learning English (IELTS, study and work in Australia).

You can look up words, search the user's word library, add words to it and see which words are due for review. \
Use the tools for facts about words and about the user's library; do not guess definitions or invent library contents.

Rules:
- Add words only when the user asks you to save, add or collect them. Never add words just because they were mentioned.
- Before adding, look the word up so the meaning is accurate. Write the meaning as a short English definition \
followed by a Chinese translation, e.g. "facts or signs showing something is true; 证据". \
Use an example sentence from the dictionary when there is one.
- If a word is already in the library, say so instead of adding it again.
- You cannot delete words or mark reviews as done; tell the user to do that in the app.
- Reply in the user's language. Keep replies short and easy to read on a phone."""

TOOLS: list[dict] = [
    {
        "name": "lookup_word",
        "description": "Look up an English word's definitions, part of speech and example sentences. "
        "Checks the offline Longman dictionary first, then an online dictionary.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"word": {"type": "string", "description": "A single English word, e.g. 'retention'"}},
            "required": ["word"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_my_words",
        "description": "Search the current user's saved words. Returns each word with its meaning, review stage "
        "(0 = new ... 5 = mastered) and next review time. Use an empty query to list recent words.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Text to match in the word or meaning; may be empty"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "add_word",
        "description": "Save a word to the current user's library. It is scheduled for review today. "
        "Only call this when the user asked to save or add words.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "word": {"type": "string", "description": "The English word"},
                "meaning": {"type": "string", "description": "Short English definition followed by a Chinese translation"},
                "example": {"type": "string", "description": "An example sentence, or an empty string"},
            },
            "required": ["word", "meaning", "example"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_due_reviews",
        "description": "List the current user's words that are due for review now, with their review stage.",
        "strict": True,
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
]


class LlmClient(Protocol):
    def create(self, *, system: str, tools: list[dict], messages: list[dict]) -> Any: ...


class ToolError(Exception):
    """A tool failed in a way the model should see and can recover from."""


class AgentTools:
    """Executes tool calls for ONE user. The user id comes from the JWT, never from the model."""

    def __init__(
        self,
        user_id: int,
        word_service: WordService,
        review_service: ReviewService,
        lookup_word: Callable[[str], dict],
    ):
        self.user_id = user_id
        self.word_service = word_service
        self.review_service = review_service
        self.lookup_word_fn = lookup_word
        self.words_added = 0

    def execute(self, name: str, tool_input: dict) -> dict:
        handler = {
            "lookup_word": self.lookup_word,
            "search_my_words": self.search_my_words,
            "add_word": self.add_word,
            "get_due_reviews": self.get_due_reviews,
        }.get(name)
        if handler is None:
            raise ToolError(f"Unknown tool: {name}")
        return handler(**tool_input)

    def lookup_word(self, word: str) -> dict:
        word = _clean_word(word)
        return self.lookup_word_fn(word)

    def search_my_words(self, query: str) -> dict:
        query = (query or "").strip().lower()
        words = self.word_service.list_words(self.user_id)
        if query:
            words = [w for w in words if query in (w.get("word") or "").lower() or query in (w.get("meaning") or "").lower()]
        return {"total": len(words), "words": [_word_summary(w) for w in words[:30]]}

    def add_word(self, word: str, meaning: str, example: str) -> dict:
        word = _clean_word(word)
        meaning = (meaning or "").strip()
        if not meaning:
            raise ToolError("meaning must not be empty")
        if self.words_added >= MAX_WORDS_ADDED_PER_REQUEST:
            raise ToolError(f"At most {MAX_WORDS_ADDED_PER_REQUEST} words can be added per message")

        existing = [w for w in self.word_service.list_words(self.user_id) if (w.get("word") or "").lower() == word]
        if existing:
            return {"added": False, "reason": "already in library", "word": _word_summary(existing[0])}

        created = self.word_service.create_word(
            self.user_id,
            {"word": word, "meaning": meaning[:500], "example": (example or "").strip()[:500], "source": "AI assistant"},
        )
        self.words_added += 1
        return {"added": True, "word": {"id": created.get("id"), "word": created.get("word"), "meaning": created.get("meaning")}}

    def get_due_reviews(self) -> dict:
        reviews = self.review_service.list_today_reviews(self.user_id)
        return {"total": len(reviews), "words": [_word_summary(w) for w in reviews[:30]]}


class AgentService:
    """Runs the tool-calling loop: call Claude -> run the tools it asks for -> send results back -> repeat."""

    def __init__(self, llm: LlmClient, tools: AgentTools):
        self.llm = llm
        self.tools = tools

    def chat(self, message: str, history: list[dict]) -> dict:
        messages = _build_messages(history, message)
        tool_calls: list[dict] = []
        usage = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0}

        for _ in range(MAX_LOOP_ITERATIONS):
            response = self.llm.create(system=SYSTEM_PROMPT, tools=TOOLS, messages=messages)
            _add_usage(usage, response)

            if response.stop_reason == "refusal":
                return _result("Sorry, I can't help with that request.", tool_calls, usage)

            if response.stop_reason == "tool_use":
                # Append the assistant turn unchanged, then answer every tool call in ONE user message.
                messages.append({"role": "assistant", "content": response.content})
                results = [self._run_tool(block, tool_calls) for block in response.content if block.type == "tool_use"]
                messages.append({"role": "user", "content": results})
                continue

            if response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": response.content})
                continue

            text = "".join(block.text for block in response.content if block.type == "text").strip()
            if response.stop_reason == "max_tokens" and not text:
                text = "The answer was too long. Please ask a narrower question."
            return _result(text or "Done.", tool_calls, usage)

        raise AppException(code=50820, message="The assistant took too many steps. Please try a simpler request.", status_code=508)

    def _run_tool(self, block: Any, tool_calls: list[dict]) -> dict:
        tool_input = block.input if isinstance(block.input, dict) else {}
        try:
            output = self.tools.execute(block.name, tool_input)
            tool_calls.append({"name": block.name, "input": tool_input, "ok": True})
            return {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(output, ensure_ascii=False, default=str)}
        except (ToolError, AppException, TypeError) as error:
            message = getattr(error, "message", None) or str(error)
            tool_calls.append({"name": block.name, "input": tool_input, "ok": False, "error": message})
            return {"type": "tool_result", "tool_use_id": block.id, "content": f"Error: {message}", "is_error": True}


def _build_messages(history: list[dict], message: str) -> list[dict]:
    """Earlier turns are sent as plain text. The list must start with a user turn and alternate roles."""
    messages: list[dict] = []
    for turn in history:
        role, content = turn.get("role"), (turn.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        if not messages and role != "user":
            continue
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n\n" + content
        else:
            messages.append({"role": role, "content": content})
    if messages and messages[-1]["role"] == "user":
        messages[-1]["content"] += "\n\n" + message
    else:
        messages.append({"role": "user", "content": message})
    return messages


def _clean_word(word: str) -> str:
    word = (word or "").strip().lower()
    if not word or len(word) > 60 or " " in word:
        raise ToolError("Provide a single English word")
    return word


def _word_summary(word: dict) -> dict:
    return {
        "id": word.get("id"),
        "word": word.get("word"),
        "meaning": (word.get("meaning") or "")[:200],
        "review_stage": word.get("review_stage"),
        "next_review_at": str(word.get("next_review_at") or ""),
    }


def _add_usage(total: dict, response: Any) -> None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    for key in total:
        total[key] += getattr(usage, key, 0) or 0


def _result(reply: str, tool_calls: list[dict], usage: dict) -> dict:
    return {"reply": reply, "tool_calls": tool_calls, "usage": usage}
