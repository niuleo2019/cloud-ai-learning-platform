"""Turn raw listening attempts into the weaknesses a study plan should target."""
from __future__ import annotations

from collections import Counter, defaultdict


def _word(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum() or ch in "'-").strip("'-")


def summarise_attempts(attempts: list[dict], top: int = 12) -> dict:
    """attempts: dicts with material_id, title, sentence_index, mode, score, expected_text, missed, wrong."""
    missed: Counter[str] = Counter()
    misheard: Counter[str] = Counter()
    examples: dict[str, str] = {}
    best: dict[tuple[int, int], dict] = {}
    scores: defaultdict[str, list[int]] = defaultdict(list)

    for attempt in attempts:
        scores[attempt["mode"]].append(int(attempt["score"]))
        for word in attempt.get("missed") or []:
            key = _word(word)
            if key:
                missed[key] += 1
                examples.setdefault(key, attempt["expected_text"])
        for pair in attempt.get("wrong") or []:
            key = _word(pair.get("expected", ""))
            if key:
                misheard[f'{key} (heard as "{_word(pair.get("actual", ""))}")'] += 1
                examples.setdefault(key, attempt["expected_text"])
        sentence = (attempt["material_id"], attempt["sentence_index"])
        current = best.get(sentence)
        if current is None or attempt["score"] > current["best_score"]:
            best[sentence] = {
                "material_id": attempt["material_id"],
                "material_title": attempt.get("title") or "",
                "sentence_index": attempt["sentence_index"],
                "text": attempt["expected_text"],
                "best_score": int(attempt["score"]),
                "attempts": (current or {}).get("attempts", 0) + 1,
            }
        else:
            current["attempts"] += 1

    weakest = sorted(best.values(), key=lambda s: (s["best_score"], -s["attempts"]))
    return {
        "attempt_count": len(attempts),
        "average_score": {mode: round(sum(v) / len(v)) for mode, v in scores.items() if v},
        "most_missed_words": [{"word": w, "times": n, "example": examples.get(w, "")} for w, n in missed.most_common(top)],
        "most_misheard_words": [{"word": w, "times": n} for w, n in misheard.most_common(top)],
        "weakest_sentences": [s for s in weakest if s["best_score"] < 90][:top],
    }
