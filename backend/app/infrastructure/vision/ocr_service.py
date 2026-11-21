import re
from collections import Counter
from dataclasses import dataclass

from app.interfaces.exceptions import AppException


WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z'-]{1,}")
COMMON_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


@dataclass
class VisionExtractionResult:
    text: str
    words: list[dict]
    total_candidates: int
    preprocessing: list[str]
    engine: str


def extract_english_words(text: str, limit: int = 40) -> list[dict]:
    """Extract normalized English word candidates from OCR text."""
    normalized_words: list[str] = []

    for match in WORD_PATTERN.findall(text):
        word = match.strip("-'").lower()
        if len(word) < 2 or word in COMMON_STOP_WORDS:
            continue
        normalized_words.append(word)

    counts = Counter(normalized_words)
    ordered_unique = list(dict.fromkeys(normalized_words))

    return [
        {
            "word": word,
            "count": counts[word],
        }
        for word in ordered_unique[:limit]
    ]


class ImageTextExtractor:
    def __init__(self, max_bytes: int = 8 * 1024 * 1024):
        self.max_bytes = max_bytes

    def extract(self, image_bytes: bytes) -> VisionExtractionResult:
        if len(image_bytes) > self.max_bytes:
            raise AppException(
                code=41301,
                message="Image is too large. Please upload an image under 8MB.",
                status_code=413,
            )

        processed_image, steps = self._preprocess(image_bytes)
        text = self._run_ocr(processed_image)
        words = extract_english_words(text)

        return VisionExtractionResult(
            text=text.strip(),
            words=words,
            total_candidates=sum(item["count"] for item in words),
            preprocessing=steps,
            engine="opencv + tesseract",
        )

    def _preprocess(self, image_bytes: bytes):
        try:
            import cv2
            import numpy as np
        except ImportError as error:
            raise AppException(
                code=50301,
                message="OpenCV is not installed. Rebuild the backend image after installing requirements.",
                status_code=503,
            ) from error

        image_array = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            raise AppException(code=40010, message="Invalid image file", status_code=400)

        steps = ["decode"]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        steps.append("grayscale")

        height, width = gray.shape[:2]
        if max(height, width) < 1200:
            scale = 1200 / max(height, width)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            steps.append("upscale")

        gray = cv2.fastNlMeansDenoising(gray, h=18)
        steps.append("denoise")

        processed = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )
        steps.append("adaptive-threshold")

        return processed, steps

    def _run_ocr(self, processed_image) -> str:
        try:
            import pytesseract
        except ImportError as error:
            raise AppException(
                code=50302,
                message="pytesseract is not installed. Rebuild the backend image after installing requirements.",
                status_code=503,
            ) from error

        try:
            return pytesseract.image_to_string(
                processed_image,
                lang="eng",
                config="--oem 3 --psm 6",
            )
        except pytesseract.TesseractNotFoundError as error:
            raise AppException(
                code=50303,
                message="Tesseract OCR engine is not available. Install tesseract-ocr or use the Docker backend.",
                status_code=503,
            ) from error
