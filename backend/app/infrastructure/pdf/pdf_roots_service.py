import json
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[3] / "data"
INDEX_FILE = DATA_DIR / "pdf_roots_index.json"
IMAGE_DIR = DATA_DIR / "pdf-root-images"


def _load_index() -> dict[str, list[dict[str, Any]]]:
    if not INDEX_FILE.exists():
        return {}

    with INDEX_FILE.open("r", encoding="utf-8") as file:
        raw_index = json.load(file)

    return {str(key).strip().lower(): value for key, value in raw_index.items()}


def find_word_in_pdfs(word: str) -> list[dict[str, Any]]:
    clean_word = word.strip().lower()
    if not clean_word:
        return []

    index = _load_index()
    entries = index.get(clean_word, [])
    pages: list[dict[str, Any]] = []

    for entry in entries:
        image_name = str(entry.get("image") or "")
        image_path = IMAGE_DIR / image_name
        if not image_name or not image_path.exists():
            continue

        pages.append(
            {
                "pdf_id": entry.get("pdf_id", ""),
                "page_num": int(entry.get("page_num", 0)),
                "title": entry.get("title", "词根词缀书籍"),
                "note": entry.get("note", ""),
                "image_url": f"/api/pdf-root-images/{image_name}",
            }
        )

    return pages


def is_available() -> bool:
    return INDEX_FILE.exists()
