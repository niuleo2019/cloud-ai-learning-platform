"""
Render one root/affix explanation area from a PDF into an image and add it to
backend/data/pdf_roots_index.json.

This script is intentionally manual-first because the provided Han Bing PDFs are
scanned images and this machine does not currently have Tesseract OCR installed.

Examples:
    python backend/scripts/render_pdf_root_entry.py --word arbitrary --pdf hanbing_vol1 --page 120

    python backend/scripts/render_pdf_root_entry.py --word arbitrary --pdf hanbing_vol1 --page 120 \
      --clip 0.08 0.20 0.92 0.62

Clip values are normalized page coordinates: x0 y0 x1 y1 from 0 to 1.
"""

import argparse
import json
import re
from pathlib import Path

import fitz


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "backend" / "data"
IMAGE_DIR = DATA_DIR / "pdf-root-images"
INDEX_FILE = DATA_DIR / "pdf_roots_index.json"

PDF_SOURCES = {
    "liuyinan": {
        "size": 20624512,
        "title": "Root Memory Magic - Liu Yinan",
    },
    "hanbing_vol1": {
        "size": 86241974,
        "title": "Words Root and Etymology 10000 - Volume 1",
    },
    "hanbing_vol2": {
        "size": 74764136,
        "title": "Words Root and Etymology 10000 - Volume 2",
    },
}


def find_pdf_path(source_id: str) -> Path:
    source = PDF_SOURCES[source_id]
    for candidate in Path("D:/").glob("*.pdf"):
        if candidate.stat().st_size == source["size"]:
            return candidate

    raise FileNotFoundError(f"Cannot find PDF on D:/ for source {source_id} by size {source['size']}")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def load_index() -> dict:
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    return {}


def save_index(index: dict) -> None:
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def render_entry(word: str, source_id: str, page_number: int, clip: list[float] | None, note: str) -> dict:
    pdf_path = find_pdf_path(source_id)
    source = PDF_SOURCES[source_id]
    page_index = page_number - 1

    doc = fitz.open(str(pdf_path))
    if page_index < 0 or page_index >= len(doc):
        doc.close()
        raise ValueError(f"Page {page_number} is outside PDF page range 1-{len(doc)}")

    page = doc[page_index]
    rect = page.rect
    clip_rect = None
    if clip:
        x0, y0, x1, y1 = clip
        clip_rect = fitz.Rect(rect.width * x0, rect.height * y0, rect.width * x1, rect.height * y1)

    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip_rect, alpha=False)
    image_name = f"{slugify(word)}-{source_id}-p{page_number}.jpg"
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    image_path = IMAGE_DIR / image_name
    pix.save(str(image_path), jpg_quality=88)
    doc.close()

    return {
        "pdf_id": source_id,
        "page_num": page_index,
        "title": source["title"],
        "image": image_name,
        "note": note,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", required=True)
    parser.add_argument("--pdf", required=True, choices=PDF_SOURCES.keys())
    parser.add_argument("--page", required=True, type=int, help="1-based PDF page number")
    parser.add_argument("--clip", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"))
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    word = args.word.strip().lower()
    entry = render_entry(word, args.pdf, args.page, args.clip, args.note)

    index = load_index()
    entries = index.setdefault(word, [])
    entries = [item for item in entries if item.get("image") != entry["image"]]
    entries.append(entry)
    index[word] = entries
    save_index(index)

    print(f"Rendered {entry['image']} and indexed it for '{word}'.")


if __name__ == "__main__":
    main()
