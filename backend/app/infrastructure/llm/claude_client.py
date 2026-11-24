import os
from contextlib import contextmanager

import anthropic

from app.infrastructure.config.settings import settings
from app.interfaces.exceptions import AppException

# If the model declines a request for safety reasons, let the API retry on a fallback model.
FALLBACK_BETAS = ["server-side-fallback-2026-07-01"]


@contextmanager
def _translate_errors():
    """Turn SDK errors into the app's error responses."""
    try:
        yield
    except anthropic.AuthenticationError as error:
        raise AppException(code=50311, message="AI assistant API key is invalid", status_code=503) from error
    except anthropic.RateLimitError as error:
        raise AppException(code=42901, message="AI assistant is busy, please try again shortly", status_code=429) from error
    except anthropic.APIStatusError as error:
        raise AppException(code=50210, message=f"AI service error ({error.status_code})", status_code=502) from error
    except anthropic.APIConnectionError as error:
        raise AppException(code=50312, message="Cannot reach the AI service", status_code=503) from error


class ClaudeClient:
    """Thin wrapper around the Anthropic SDK.

    The application layer only calls `create(...)` / `generate_text(...)`, so services
    do not depend on SDK details and can be unit-tested with a fake client.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None, effort: str | None = None):
        key = api_key or settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise AppException(
                code=50310,
                message="AI assistant is not configured. Set ANTHROPIC_API_KEY for the backend.",
                status_code=503,
            )
        self.model = model or settings.agent_model
        self.effort = effort or settings.agent_effort
        self._client = anthropic.Anthropic(api_key=key, timeout=60.0, max_retries=2)

    def create(self, *, system: str, tools: list[dict], messages: list[dict]):
        with _translate_errors():
            return self._client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=system,
                tools=tools,
                messages=messages,
                thinking={"type": "adaptive"},
                output_config={"effort": self.effort},
                # Cache the stable prefix (system prompt + tools + earlier turns) across loop iterations.
                cache_control={"type": "ephemeral"},
                betas=FALLBACK_BETAS,
                fallbacks="default",
            )

    def generate_text(self, *, system: str, prompt: str, max_tokens: int = 16000) -> dict:
        """One long answer (e.g. a full word explanation).

        Streamed, so a multi-thousand-token answer never hits a request timeout;
        the 60 s client timeout then applies to gaps between chunks, not the whole answer.
        """
        with _translate_errors():
            with self._client.beta.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                thinking={"type": "adaptive"},
                output_config={"effort": self.effort},
                # The long system prompt is identical for every word: cache it.
                cache_control={"type": "ephemeral"},
                betas=FALLBACK_BETAS,
                fallbacks="default",
            ) as stream:
                message = stream.get_final_message()
        text = "".join(block.text for block in message.content if block.type == "text")
        usage = message.usage
        return {
            "text": text,
            "stop_reason": message.stop_reason,
            "model": getattr(message, "model", self.model),
            "usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
            },
        }
