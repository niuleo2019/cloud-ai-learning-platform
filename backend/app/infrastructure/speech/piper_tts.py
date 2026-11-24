"""Natural-sounding sentence audio with Piper (local neural TTS, runs on CPU, no API cost).

Used for example sentences that have no real recording. The voice model (.onnx + .onnx.json)
lives in settings.tts_voice_path; download it once with:
    python -m piper.download_voices en_GB-alba-medium --data-dir /app/data/tts-voices
(Voice "alba": University of Edinburgh dataset, CC BY 4.0.)
"""
from __future__ import annotations

import io
import threading
import wave
from functools import lru_cache
from pathlib import Path

from app.infrastructure.config.settings import settings
from app.interfaces.exceptions import AppException

_voice = None
_lock = threading.Lock()


def is_available() -> bool:
    return Path(settings.tts_voice_path).exists()


def _get_voice():
    global _voice
    if _voice is None:
        with _lock:
            if _voice is None:
                if not is_available():
                    raise AppException(50330, "Sentence audio is not set up on the server", 503)
                try:
                    from piper import PiperVoice
                except ImportError as error:
                    raise AppException(50331, "Sentence audio (Piper) is not installed on the server", 503) from error
                _voice = PiperVoice.load(settings.tts_voice_path)
    return _voice


@lru_cache(maxsize=512)
def synthesize_wav(text: str) -> bytes:
    voice = _get_voice()
    buffer = io.BytesIO()
    with _lock, wave.open(buffer, "wb") as wav:
        voice.synthesize_wav(text, wav)
    return buffer.getvalue()


def warm_up() -> None:
    try:
        if is_available():
            synthesize_wav("Hello.")
    except Exception:  # noqa: BLE001 - best effort
        pass
