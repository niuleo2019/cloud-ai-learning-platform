"""Local speech recognition with faster-whisper (runs on CPU, no API cost).

The model is downloaded once into ``settings.whisper_models_dir`` and kept in memory.
A lock serialises recognition so a long listening file and a short retell clip
never compete for the CPU at the same time.
"""
from __future__ import annotations

import io
import threading

from app.domain.services.sentence_splitter import TimedWord, split_into_sentences
from app.infrastructure.config.settings import settings
from app.interfaces.exceptions import AppException

_model = None
_model_lock = threading.Lock()
_run_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    from faster_whisper import WhisperModel
                except ImportError as error:
                    raise AppException(50320, "Speech recognition is not installed on the server", 503) from error
                _model = WhisperModel(
                    settings.whisper_model,
                    device="cpu",
                    compute_type="int8",
                    download_root=settings.whisper_models_dir,
                )
    return _model


def transcribe_to_sentences(audio_path: str) -> dict:
    """Transcribe a listening file into timed sentences for practice."""
    model = _get_model()
    with _run_lock:
        segments, info = model.transcribe(
            audio_path,
            language="en",
            word_timestamps=True,
            vad_filter=True,
            beam_size=5,
        )
        words = [
            TimedWord(text=word.word, start=word.start, end=word.end)
            for segment in segments
            for word in (segment.words or [])
        ]
    return {
        "duration": round(info.duration, 2),
        "sentences": split_into_sentences(words, duration=info.duration),
    }


def transcribe_clip(audio_bytes: bytes) -> str:
    """Transcribe a short recording (a retell attempt).

    No prompt with the expected sentence is given on purpose: biasing the
    recogniser toward the right answer would hide the learner's mistakes.
    """
    model = _get_model()
    with _run_lock:
        segments, _info = model.transcribe(
            io.BytesIO(audio_bytes),
            language="en",
            beam_size=5,
            condition_on_previous_text=False,
            vad_filter=False,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
