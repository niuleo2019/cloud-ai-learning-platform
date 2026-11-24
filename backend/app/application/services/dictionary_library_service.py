"""Imported MDict dictionaries (like Eudic / GoldenDict): import, manage, look up, serve resources."""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import BinaryIO

from app.domain.repositories.dictionary_repository import DictionaryRepository
from app.infrastructure.dictionary.dictionary_files import DictionaryFiles, examples_with_audio, mdd_files_for
from app.infrastructure.dictionary.mdict import MdictError, MdxFile
from app.interfaces.exceptions import AppException

logger = logging.getLogger(__name__)

# Files a dictionary package may contain besides the .mdx / .mdd.
ALLOWED_EXTENSIONS = {
    ".mdx", ".mdd", ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp",
    ".ttf", ".otf", ".woff", ".woff2", ".mp3", ".wav", ".ogg", ".spx", ".txt", ".ini",
}
RESOURCE_LINK_SECONDS = 24 * 3600
CHUNK = 1024 * 1024


class DictionaryLibraryService:
    def __init__(
        self,
        repository: DictionaryRepository,
        files: DictionaryFiles,
        secret: str,
        max_upload_bytes: int,
    ):
        self.repository = repository
        self.files = files
        self.root = files.root
        self.secret = secret.encode()
        self.max_upload_bytes = max_upload_bytes

    # ------------------------------------------------------------------ list / manage

    def list_dictionaries(self) -> list[dict]:
        return [self._public(row) for row in self.repository.list_all()]

    @staticmethod
    def _public(row: dict) -> dict:
        return {
            "id": row["id"],
            "title": row["title"],
            "mdx_file": row["mdx_file"],
            "mdd_files": row.get("mdd_files") or [],
            "entry_count": row.get("entry_count", 0),
            "enabled": bool(row.get("enabled")),
            "sort_order": row.get("sort_order", 0),
        }

    def _get(self, dictionary_id: int) -> dict:
        row = self.repository.find_by_id(dictionary_id)
        if not row:
            raise AppException(40440, "Dictionary not found", 404)
        return row

    def update(self, dictionary_id: int, title: str | None, enabled: bool | None) -> dict:
        self._get(dictionary_id)
        fields: dict = {}
        if title is not None:
            clean = " ".join(title.split())
            if not clean:
                raise AppException(40040, "Title cannot be empty", 400)
            fields["title"] = clean[:200]
        if enabled is not None:
            fields["enabled"] = 1 if enabled else 0
        return self._public(self.repository.update(dictionary_id, fields))

    def reorder(self, ordered_ids: list[int]) -> list[dict]:
        known = {row["id"] for row in self.repository.list_all()}
        if set(ordered_ids) != known or len(ordered_ids) != len(known):
            raise AppException(40041, "The order must list every dictionary exactly once", 400)
        self.repository.set_order(ordered_ids)
        return self.list_dictionaries()

    def delete(self, dictionary_id: int) -> dict:
        row = self._get(dictionary_id)
        self.repository.delete(dictionary_id)
        self.files.forget(dictionary_id)
        folder = self.files.folder_of(row)
        others = [r for r in self.repository.list_all() if r["folder"] == row["folder"]]
        if not others and folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
        return {"id": dictionary_id}

    # ------------------------------------------------------------------ import

    def import_files(self, user_id: int, uploads: list[tuple[str, BinaryIO]]) -> list[dict]:
        """Save an uploaded dictionary package (.mdx + optional .mdd/css/js/images) and register it."""
        names = [Path(name or "").name for name, _ in uploads]
        if not any(name.lower().endswith(".mdx") for name in names):
            raise AppException(40042, "Please include the .mdx file (the .mdd files are optional)", 400)
        for name in names:
            if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
                raise AppException(40043, f"Unsupported file in dictionary package: {name}", 400)

        mdx_name = next(name for name in names if name.lower().endswith(".mdx"))
        folder_name = f"{_slug(Path(mdx_name).stem)}-{uuid.uuid4().hex[:8]}"
        folder = self.root / folder_name
        folder.mkdir(parents=True, exist_ok=False)
        try:
            written = 0
            for (_, stream), name in zip(uploads, names):
                with (folder / name).open("wb") as target:
                    while chunk := stream.read(CHUNK):
                        written += len(chunk)
                        if written > self.max_upload_bytes:
                            raise AppException(41340, "Dictionary files are too large", 413)
                        target.write(chunk)
            created = self._register_folder(folder, user_id)
            if not created:
                raise AppException(40044, "No readable .mdx dictionary was found in the upload", 400)
            return created
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            raise

    def scan(self, user_id: int) -> dict:
        """Register dictionaries copied straight into the dictionaries folder (best for big .mdd files)."""
        self.root.mkdir(parents=True, exist_ok=True)
        # A loose .mdx in the root gets its own folder together with its resource files.
        for mdx_path in sorted(self.root.glob("*.mdx")):
            folder = self.root / f"{_slug(mdx_path.stem)}-{uuid.uuid4().hex[:8]}"
            folder.mkdir()
            for related in [mdx_path, *(self.root / name for name in mdd_files_for(mdx_path))]:
                shutil.move(str(related), folder / related.name)

        registered = {(row["folder"], row["mdx_file"]) for row in self.repository.list_all()}
        added: list[dict] = []
        errors: list[dict] = []
        for folder in sorted(p for p in self.root.iterdir() if p.is_dir()):
            pending = [m for m in folder.glob("*.mdx") if (folder.name, m.name) not in registered]
            if not pending:
                continue
            try:
                added.extend(self._register_folder(folder, user_id, only=pending))
            except AppException as error:
                errors.append({"folder": folder.name, "message": error.message})
        return {"added": added, "errors": errors}

    def _register_folder(self, folder: Path, user_id: int, only: list[Path] | None = None) -> list[dict]:
        created = []
        for mdx_path in only or sorted(folder.glob("*.mdx")):
            try:
                mdx = MdxFile(mdx_path)
            except MdictError as error:
                raise AppException(42240, f"{mdx_path.name}: {error}", 422) from error
            row = self.repository.create(
                {
                    "title": (mdx.title or mdx_path.stem)[:200],
                    "folder": folder.name,
                    "mdx_file": mdx_path.name,
                    "mdd_files": mdd_files_for(mdx_path),
                    "entry_count": mdx.entry_count,
                    "uploaded_by": user_id,
                }
            )
            created.append(self._public(row))
        return created

    # ------------------------------------------------------------------ lookup

    def lookup(self, word: str) -> dict:
        word = word.strip()
        results = []
        enabled = [row for row in self.repository.list_all() if row.get("enabled")]
        for row in enabled:
            try:
                entries = self.files.open(row).lookup(word)
            except (MdictError, OSError) as error:
                logger.warning("Dictionary %s could not be read: %s", row["id"], error)
                results.append({"id": row["id"], "title": row["title"], "found": False, "error": "unreadable"})
                continue
            results.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "found": bool(entries),
                    "entries": entries,
                    "resource_base": self.resource_base(row["id"]) if entries else None,
                }
            )
        return {"word": word, "enabled_count": len(enabled), "results": results}

    def examples(self, word: str, limit: int = 6) -> dict:
        """Example sentences that come with a real recording, from the first enabled dictionary that has them."""
        for row in self.repository.list_all():
            if not row.get("enabled") or not row.get("mdd_files"):
                continue
            try:
                entries = self.files.open(row).lookup(word.strip())
            except (MdictError, OSError):
                continue
            seen: set[str] = set()
            items = []
            for entry in entries:
                for text, sound in examples_with_audio(entry):
                    if text.lower() in seen:
                        continue
                    seen.add(text.lower())
                    items.append({"text": text, "audio": sound})
            if items:
                return {
                    "dictionary": row["title"],
                    "resource_base": self.resource_base(row["id"]),
                    "examples": items[:limit],
                }
        return {"dictionary": None, "resource_base": None, "examples": []}

    def suggest(self, prefix: str, limit: int = 10) -> list[str]:
        seen: dict[str, None] = {}
        for row in self.repository.list_all():
            if not row.get("enabled"):
                continue
            try:
                for word in self.files.open(row).mdx.suggest(prefix, limit):
                    seen.setdefault(word, None)
            except (MdictError, OSError):
                continue
            if len(seen) >= limit:
                break
        return list(seen)[:limit]

    # ------------------------------------------------------------------ resources (css, images, audio)

    def resource_base(self, dictionary_id: int) -> str:
        """Relative URL prefix for an entry's resources, signed so <img>/<link>/<audio> need no login header.

        The expiry is rounded to the hour so the same URL (and the browser cache) is reused.
        """
        expires = (int(time.time()) // 3600 + 1) * 3600 + RESOURCE_LINK_SECONDS
        return f"/dictionaries/{dictionary_id}/res/{expires}-{self._sign(dictionary_id, expires)}/"

    def _sign(self, dictionary_id: int, expires: int) -> str:
        return hmac.new(self.secret, f"dict:{dictionary_id}:{expires}".encode(), hashlib.sha256).hexdigest()[:32]

    def resource(self, dictionary_id: int, token: str, path: str) -> tuple[bytes, str]:
        try:
            expires_text, signature = token.split("-", 1)
            expires = int(expires_text)
        except ValueError as error:
            raise AppException(40340, "Invalid resource link", 403) from error
        if expires < time.time() or not hmac.compare_digest(signature, self._sign(dictionary_id, expires)):
            raise AppException(40340, "Resource link expired; look the word up again", 403)
        row = self._get(dictionary_id)
        found = self.files.open(row).resource(path)
        if found is None:
            raise AppException(40441, "Resource not found in this dictionary", 404)
        return found

    def warm_up(self) -> None:
        """Open enabled dictionaries in the background so the first lookup is fast."""
        for row in self.repository.list_all():
            if row.get("enabled"):
                try:
                    self.files.open(row)
                except Exception:  # noqa: BLE001 - best effort
                    logger.warning("Could not pre-open dictionary %s", row["id"])


def _slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return slug[:40] or "dictionary"
