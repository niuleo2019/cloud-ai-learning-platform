import html
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_DICTIONARY_PATH = Path(__file__).resolve().parents[3] / "data" / "longman_dictionary.json"


def _strip_html(value: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", value, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalise_entry(word: str, raw_value: Any) -> dict:
    if isinstance(raw_value, dict):
        raw_html = str(raw_value.get("html") or raw_value.get("raw") or "")
        text = str(raw_value.get("text") or _strip_html(raw_html))
        audio = str(raw_value.get("audio") or "")
    else:
        raw_html = str(raw_value)
        text = _strip_html(raw_html)
        audio = ""

    short_text = text[:1200]
    return {
        "word": word,
        "html": raw_html,
        "text": short_text,
        "audio": audio,
        "source": "Longman offline",
    }


@lru_cache(maxsize=1)
def _load_dictionary() -> dict[str, Any]:
    configured_path = os.getenv("LONGMAN_DICTIONARY_PATH")
    dictionary_path = Path(configured_path) if configured_path else DEFAULT_DICTIONARY_PATH

    if not dictionary_path.exists():
        return {}

    with dictionary_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def lookup_longman_word(word: str) -> dict:
    clean_word = word.strip().lower()
    dictionary = _load_dictionary()
    raw_value = dictionary.get(clean_word)

    if raw_value is None:
        return {"found": False, "word": clean_word}

    return {"found": True, **_normalise_entry(clean_word, raw_value)}
