"""Opened MDict dictionaries on disk: entry lookup and resource (css/js/image/audio) access.

Each imported dictionary lives in its own folder under ``settings.dictionaries_dir``:
the .mdx, its .mdd files (``name.mdd``, ``name.1.mdd``, ...) and any loose css/js/fonts
that some dictionaries ship next to the .mdx.
"""
from __future__ import annotations

import html as html_lib
import mimetypes
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from app.infrastructure.dictionary.longman_audio import speex_to_wav
from app.infrastructure.dictionary.mdict import MddFile, MdxFile

RESOURCE_TYPES = {
    ".spx": "audio/wav",  # converted: browsers cannot play Speex
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
}


_EXAMPLE_WITH_SOUND = re.compile(
    # one <a href="sound://..."> ... </a> (never spanning into another link) directly followed by <ex>
    r'<a\s[^>]*href="sound://([^"]+?\.(?:spx|mp3|wav|ogg))"[^>]*>(?:(?!</a>).)*</a>\s*<ex>(.*?)</ex>',
    re.IGNORECASE | re.DOTALL,
)


def examples_with_audio(entry_html: str) -> list[tuple[str, str]]:
    """(sentence, sound file) pairs: a sound:// link directly followed by an <ex> example (LDOCE style)."""
    pairs = []
    for sound, body in _EXAMPLE_WITH_SOUND.findall(entry_html):
        text = html_lib.unescape(re.sub(r"<[^>]+>", "", body))
        text = " ".join(text.split())
        if len(text.split()) >= 3:
            pairs.append((text, sound))
    return pairs


def mdd_files_for(mdx_path: Path) -> list[str]:
    """``name.mdd`` first, then ``name.1.mdd``, ``name.2.mdd`` ... (MDict's split-resource convention)."""
    stem = mdx_path.stem
    found = []
    for candidate in sorted(mdx_path.parent.glob("*.mdd"), key=lambda p: p.name.lower()):
        name = candidate.name
        if name.lower() == f"{stem}.mdd".lower() or re.fullmatch(rf"{re.escape(stem)}\.\d+\.mdd", name, re.IGNORECASE):
            found.append(name)
    found.sort(key=lambda n: (0, 0) if n.lower() == f"{stem}.mdd".lower() else (1, int(n.split(".")[-2])))
    if not found:
        # Folders imported together often name the resource file differently ("LDOCE5 audio.mdd").
        found = sorted(p.name for p in mdx_path.parent.glob("*.mdd"))
    return found


@dataclass
class OpenedDictionary:
    folder: Path
    mdx: MdxFile
    mdds: list[MddFile]

    def lookup(self, word: str) -> list[str]:
        return self.mdx.lookup(word)

    def resource(self, path: str) -> tuple[bytes, str] | None:
        clean = path.split("?")[0].split("#")[0].strip().replace("\\", "/").lstrip("/")
        if not clean or ".." in clean.split("/"):
            return None
        data = None
        for mdd in self.mdds:
            data = mdd.get(clean)
            if data is not None:
                break
        if data is None:
            candidate = (self.folder / clean).resolve()
            if candidate.is_file() and self.folder.resolve() in candidate.parents:
                data = candidate.read_bytes()
        if data is None:
            return None

        extension = Path(clean).suffix.lower()
        if extension == ".spx":
            return speex_to_wav(data), RESOURCE_TYPES[".spx"]
        content_type = RESOURCE_TYPES.get(extension) or mimetypes.guess_type(clean)[0] or "application/octet-stream"
        return data, content_type


class DictionaryFiles:
    """Process-wide cache of opened dictionaries (opening reads the key index once)."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._opened: dict[int, tuple[str, OpenedDictionary]] = {}
        self._lock = threading.Lock()

    def folder_of(self, row: dict) -> Path:
        folder = (self.root / row["folder"]).resolve()
        if self.root.resolve() not in folder.parents:
            raise ValueError("Dictionary folder is outside the dictionaries directory")
        return folder

    def open(self, row: dict) -> OpenedDictionary:
        signature = f'{row["folder"]}/{row["mdx_file"]}/{",".join(row.get("mdd_files") or [])}'
        cached = self._opened.get(row["id"])
        if cached and cached[0] == signature:
            return cached[1]
        with self._lock:
            cached = self._opened.get(row["id"])
            if cached and cached[0] == signature:
                return cached[1]
            folder = self.folder_of(row)
            opened = OpenedDictionary(
                folder=folder,
                mdx=MdxFile(folder / row["mdx_file"]),
                mdds=[MddFile(folder / name) for name in row.get("mdd_files") or [] if (folder / name).exists()],
            )
            self._opened[row["id"]] = (signature, opened)
            return opened

    def forget(self, dictionary_id: int) -> None:
        with self._lock:
            self._opened.pop(dictionary_id, None)
