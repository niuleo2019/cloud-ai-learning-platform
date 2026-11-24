"""Listening practice: sentence splitting, service rules and Longman audio naming (no model, no DB)."""
import pytest

from app.application.services.listening_service import ListeningService
from app.domain.services.sentence_splitter import TimedWord, split_into_sentences
from app.infrastructure.dictionary.longman_audio import parse_clip_name
from app.infrastructure.dictionary.mdict_resource import ripemd128
from app.interfaces.exceptions import AppException


def words(*items):
    return [TimedWord(text, start, end) for text, start, end in items]


# -- sentence splitter ---------------------------------------------------------


def test_splits_at_sentence_punctuation_with_padding():
    result = split_into_sentences(
        words(
            (" Good", 0.5, 0.8), (" morning.", 0.8, 1.2),
            (" How", 1.6, 1.8), (" are", 1.8, 1.9), (" you?", 1.9, 2.3),
        ),
        duration=3.0,
    )
    assert [s["text"] for s in result] == ["Good morning.", "How are you?"]
    assert result[0]["start"] == pytest.approx(0.35)
    # Padding never overlaps the neighbouring sentence.
    assert result[0]["end"] <= result[1]["start"] + 1e-9 or result[0]["end"] <= 1.6
    assert result[1]["end"] == pytest.approx(2.6)


def test_does_not_split_after_title_abbreviation_or_lowercase_continuation():
    result = split_into_sentences(
        words(
            (" Ask", 0, 0.2), (" Mr.", 0.2, 0.4), (" Smith", 0.4, 0.7), (" at", 0.7, 0.8),
            (" 3", 0.8, 0.9), (" p.m.", 0.9, 1.1), (" today.", 1.1, 1.5),
        )
    )
    assert [s["text"] for s in result] == ["Ask Mr. Smith at 3 p.m. today."]


def test_long_pause_starts_a_new_sentence():
    result = split_into_sentences(words((" first", 0, 0.5), (" part", 0.5, 1.0), (" second", 3.0, 3.5)))
    assert [s["text"] for s in result] == ["first part", "second"]


def test_run_on_speech_is_cut_at_a_comma():
    items = [(f" w{i}", i * 0.2, i * 0.2 + 0.2) for i in range(30)]
    items[29] = (" w29,", 29 * 0.2, 29 * 0.2 + 0.2)
    items.append((" tail", 6.2, 6.4))
    result = split_into_sentences(words(*items), max_words=28)
    assert len(result) == 2
    assert result[0]["text"].endswith("w29,")


# -- service -------------------------------------------------------------------


class FakeRepository:
    def __init__(self):
        self.rows = {}
        self.failed = {}

    def create(self, user_id, title, audio_file, original_filename):
        row = {"id": len(self.rows) + 1, "user_id": user_id, "title": title, "audio_file": audio_file,
               "status": "processing", "sentences": None}
        self.rows[row["id"]] = row
        return dict(row)

    def list_by_user(self, user_id):
        return [r for r in self.rows.values() if r["user_id"] == user_id]

    def find_by_id_and_user(self, material_id, user_id):
        row = self.rows.get(material_id)
        return dict(row) if row and row["user_id"] == user_id else None

    def mark_ready(self, material_id, duration, sentences):
        self.rows[material_id].update(status="ready", sentences=sentences)

    def update_sentences(self, material_id, user_id, sentences):
        self.rows[material_id]["sentences"] = sentences

    def mark_failed(self, material_id, error_message):
        self.rows[material_id]["status"] = "failed"
        self.failed[material_id] = error_message

    def delete(self, material_id, user_id):
        return self.rows.pop(material_id, None) is not None


def make_service(tmp_path, transcribe_file=None):
    return ListeningService(
        FakeRepository(),
        storage_dir=tmp_path,
        transcribe_file=transcribe_file or (lambda path: {"duration": 2.0, "sentences": [{"index": 0, "start": 0, "end": 2, "text": "Hi."}]}),
        transcribe_clip=lambda data: "hello there",
        max_upload_bytes=1024,
    )


def test_upload_saves_file_per_user_and_transcribes(tmp_path):
    service = make_service(tmp_path)
    material = service.create_material(7, "  Test 1 ", "section1.MP3", b"abc")
    assert material["title"] == "Test 1"
    assert material["audio_file"].startswith("7/") and material["audio_file"].endswith(".mp3")
    assert (tmp_path / material["audio_file"]).read_bytes() == b"abc"

    service.process_material(material["id"], material["audio_file"])
    assert service.get_material(7, material["id"])["status"] == "ready"


def test_rejects_non_audio_and_oversized_files(tmp_path):
    service = make_service(tmp_path)
    with pytest.raises(AppException):
        service.create_material(7, "", "notes.pdf", b"abc")
    with pytest.raises(AppException):
        service.create_material(7, "", "big.mp3", b"x" * 2048)


def test_transcription_error_marks_material_failed(tmp_path):
    def broken(path):
        raise RuntimeError("decoder crashed")

    service = make_service(tmp_path, transcribe_file=broken)
    material = service.create_material(7, "", "a.mp3", b"abc")
    service.process_material(material["id"], material["audio_file"])
    assert service.repository.rows[material["id"]]["status"] == "failed"


def test_other_users_cannot_read_or_delete(tmp_path):
    service = make_service(tmp_path)
    material = service.create_material(7, "", "a.mp3", b"abc")
    with pytest.raises(AppException):
        service.get_material(8, material["id"])
    with pytest.raises(AppException):
        service.delete_material(8, material["id"])


def test_sentence_text_can_be_corrected(tmp_path):
    service = make_service(tmp_path)
    material = service.create_material(7, "", "a.mp3", b"abc")
    service.process_material(material["id"], material["audio_file"])
    updated = service.update_sentence_text(7, material["id"], 0, "  Hi   there. ")
    assert updated["text"] == "Hi there." and updated["edited"] is True
    with pytest.raises(AppException):
        service.update_sentence_text(7, material["id"], 5, "x")


def test_delete_removes_audio_file(tmp_path):
    service = make_service(tmp_path)
    material = service.create_material(7, "", "a.mp3", b"abc")
    service.delete_material(7, material["id"])
    assert not (tmp_path / material["audio_file"]).exists()


# -- Longman audio -------------------------------------------------------------


def test_ripemd128_known_vectors():
    assert ripemd128(b"").hex() == "cdf26213a150dc3ecb610f18f6b38b46"
    assert ripemd128(b"abc").hex() == "c14a12199c66e4ba84636b0f69144c77"


@pytest.mark.parametrize(
    "name, expected",
    [
        ("us_retention.spx", ("us", "retention", 0)),
        ("gb_allocate0205.spx", ("gb", "allocate", 1)),
        ("gb_ld41retention.spx", ("gb", "retention", 2)),
        ("gb_evidence_n0205.spx", ("gb", "evidence", 2)),
        ("us_run1.spx", ("us", "run", 1)),
        ("gb_tennis_court0205.spx", ("gb", "tennis court", 1)),
        ("gb_p028__000006015.spx", None),
        ("ldoce5_exa000001.spx", None),
        ("abacus.jpg", None),
    ],
)
def test_parse_clip_name(name, expected):
    assert parse_clip_name(name) == expected
