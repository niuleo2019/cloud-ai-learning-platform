"""Group word-level timestamps from speech recognition into practice sentences."""
from __future__ import annotations

from dataclasses import dataclass

SENTENCE_END = (".", "?", "!")
ABBREVIATIONS = {"mr.", "mrs.", "ms.", "dr.", "st.", "prof.", "mt."}


@dataclass(frozen=True)
class TimedWord:
    text: str  # as recognised, may carry a leading space and punctuation
    start: float
    end: float


def split_into_sentences(
    words: list[TimedWord],
    *,
    max_words: int = 28,
    pause_seconds: float = 1.2,
    lead_in: float = 0.15,
    tail: float = 0.3,
    duration: float | None = None,
) -> list[dict]:
    """Split at sentence punctuation, long pauses, or (for run-on speech) at a comma once too long.

    Each sentence gets a little padding so the first and last syllables are not clipped,
    without overlapping its neighbours.
    """
    groups: list[list[TimedWord]] = []
    current: list[TimedWord] = []
    for index, word in enumerate(words):
        if not word.text.strip():
            continue
        if current and word.start - current[-1].end >= pause_seconds:
            groups.append(current)
            current = []
        current.append(word)
        token = word.text.strip()
        next_starts_upper = index + 1 < len(words) and words[index + 1].text.strip()[:1].isupper()
        too_long = len(current) >= max_words and token.endswith((",", ";", ":"))
        is_end = token.endswith(SENTENCE_END) and token.lower() not in ABBREVIATIONS
        if is_end and (next_starts_upper or index + 1 == len(words)) or too_long:
            groups.append(current)
            current = []
        elif len(current) >= max_words * 2:
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    sentences = []
    for index, group in enumerate(groups):
        previous_end = groups[index - 1][-1].end if index > 0 else 0.0
        next_start = groups[index + 1][0].start if index + 1 < len(groups) else (duration or group[-1].end + tail)
        start = max(previous_end, group[0].start - lead_in, 0.0)
        end = min(next_start, group[-1].end + tail)
        sentences.append(
            {
                "index": index,
                "start": round(start, 2),
                "end": round(max(end, start + 0.2), 2),
                "text": "".join(word.text for word in group).strip(),
            }
        )
    return sentences
