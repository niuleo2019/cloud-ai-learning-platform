"""Listening practice: import audio, transcribe it into timed sentences, check retell attempts."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Callable

from app.domain.repositories.listening_repository import ListeningRepository
from app.interfaces.exceptions import AppException

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".oga", ".opus", ".webm", ".flac", ".mp4"}
MAX_RETELL_BYTES = 5 * 1024 * 1024


class ListeningService:
    def __init__(
        self,
        repository: ListeningRepository,
        storage_dir: str | Path,
        transcribe_file: Callable[[str], dict],
        transcribe_clip: Callable[[bytes], str],
        max_upload_bytes: int,
    ):
        self.repository = repository
        self.storage_dir = Path(storage_dir)
        self.transcribe_file = transcribe_file
        self.transcribe_clip = transcribe_clip
        self.max_upload_bytes = max_upload_bytes

    # -- materials -----------------------------------------------------------

    def create_material(self, user_id: int, title: str, filename: str, data: bytes) -> dict:
        extension = Path(filename or "").suffix.lower()
        if extension not in AUDIO_EXTENSIONS:
            raise AppException(40020, "Please upload an audio file (mp3, m4a, wav, ogg, webm)", 400)
        if not data:
            raise AppException(40021, "The audio file is empty", 400)
        if len(data) > self.max_upload_bytes:
            raise AppException(40022, f"Audio must be under {self.max_upload_bytes // (1024 * 1024)}MB", 413)

        relative = Path(str(user_id)) / f"{uuid.uuid4().hex}{extension}"
        target = self.storage_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

        clean_title = (title or "").strip() or Path(filename).stem or "Listening"
        return self.repository.create(user_id, clean_title[:200], relative.as_posix(), filename[:255])

    def process_material(self, material_id: int, audio_file: str) -> None:
        """Runs after the upload response (background task): transcribe and store sentences."""
        try:
            result = self.transcribe_file(str(self.storage_dir / audio_file))
            if not result["sentences"]:
                self.repository.mark_failed(material_id, "No English speech was detected in this audio")
                return
            self.repository.mark_ready(material_id, result["duration"], result["sentences"])
        except Exception as error:  # noqa: BLE001 - any failure must end the 'processing' state
            logger.exception("Listening transcription failed for material %s", material_id)
            message = error.message if isinstance(error, AppException) else "Speech recognition failed for this file"
            self.repository.mark_failed(material_id, message)

    def list_materials(self, user_id: int) -> list[dict]:
        return self.repository.list_by_user(user_id)

    def get_material(self, user_id: int, material_id: int) -> dict:
        material = self.repository.find_by_id_and_user(material_id, user_id)
        if not material:
            raise AppException(40420, "Listening material not found", 404)
        return material

    def get_audio_path(self, user_id: int, material_id: int) -> Path:
        material = self.get_material(user_id, material_id)
        path = self.storage_dir / material["audio_file"]
        if not path.exists():
            raise AppException(40421, "Audio file is missing on the server", 404)
        return path

    def update_sentence_text(self, user_id: int, material_id: int, index: int, text: str) -> dict:
        """Correct a sentence the recogniser got wrong (e.g. paste the official transcript)."""
        material = self.get_material(user_id, material_id)
        sentences = material.get("sentences") or []
        if not 0 <= index < len(sentences):
            raise AppException(40422, "Sentence not found", 404)
        clean = " ".join(text.split())
        if not clean:
            raise AppException(40025, "Sentence text cannot be empty", 400)
        sentences[index] = {**sentences[index], "text": clean, "edited": True}
        self.repository.update_sentences(material_id, user_id, sentences)
        return sentences[index]

    def delete_material(self, user_id: int, material_id: int) -> dict:
        material = self.get_material(user_id, material_id)
        self.repository.delete(material_id, user_id)
        (self.storage_dir / material["audio_file"]).unlink(missing_ok=True)
        return {"id": material_id}

    # -- retell --------------------------------------------------------------

    def recognise_retell(self, data: bytes) -> dict:
        if not data:
            raise AppException(40023, "The recording is empty", 400)
        if len(data) > MAX_RETELL_BYTES:
            raise AppException(40024, "The recording is too long; keep it to one sentence", 413)
        try:
            text = self.transcribe_clip(data)
        except AppException:
            raise
        except Exception as error:  # noqa: BLE001
            logger.exception("Retell recognition failed")
            raise AppException(42220, "Could not read this recording. Please try again.", 422) from error
        return {"text": text}
