from app.infrastructure.vision.ocr_service import extract_english_words


def test_extract_english_words_normalizes_and_counts_candidates():
    text = "Evidence, evidence! The researchers observed arbitrary standards in IELTS reading."

    words = extract_english_words(text)

    assert words[:5] == [
        {"word": "evidence", "count": 2},
        {"word": "researchers", "count": 1},
        {"word": "observed", "count": 1},
        {"word": "arbitrary", "count": 1},
        {"word": "standards", "count": 1},
    ]
