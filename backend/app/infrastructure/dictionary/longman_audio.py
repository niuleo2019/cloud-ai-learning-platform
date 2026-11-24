"""Longman pronunciation audio from the LDOCE .mdd resource file.

The .mdd stores Speex clips named after headwords, with editorial prefixes and
suffixes, e.g. ``us_retention.spx``, ``gb_ld41retention.spx``,
``gb_allocate0205.spx``, ``gb_evidence_n0205.spx``, ``us_run1.spx``.
We build a ``word -> {accent: clip name}`` index once and convert a clip to
WAV on request, because browsers cannot play Speex.
"""
from __future__ import annotations

import io
import re
import threading
import wave
from functools import lru_cache
from pathlib import Path

from app.infrastructure.config.settings import settings
from app.infrastructure.dictionary.mdict_resource import MdictResourceFile

ACCENTS = ("gb", "us")
_PREFIX = re.compile(r"^(ld4\d|ld5_|brelasde|laad|lpd_)")
_POS_SUFFIX = re.compile(r"_(n|v|adj|adv|prep|pron|det|conj|interj|pre)$")

_lock = threading.Lock()
_resource: MdictResourceFile | None = None
_index: dict[str, dict[str, tuple[int, str]]] | None = None


def parse_clip_name(name: str) -> tuple[str, str, int] | None:
    """Return (accent, word, rank) for a headword clip; lower rank = better match."""
    if not name.endswith(".spx") or name[:3] not in ("gb_", "us_"):
        return None
    accent, base = name[:2], name[3:-4]
    if base.startswith("p028__"):
        return None  # numbered phrase recordings, not headwords

    rank = 0
    if base.endswith("0205"):
        base, rank = base[:-4], 1
    if _PREFIX.match(base):
        base, rank = _PREFIX.sub("", base), 2
    if base.endswith("_las3_br"):
        base, rank = base[: -len("_las3_br")], 2
    stripped = _POS_SUFFIX.sub("", base)
    if stripped != base:
        base, rank = stripped, rank + 1
    if re.search(r"[a-z]\d$", base):
        base, rank = base[:-1], rank + 1

    word = base.replace("__", " ").replace("_", " ").strip()
    if not word or not re.fullmatch(r"[a-z][a-z' .-]*", word):
        return None
    return accent, word, rank


def _load() -> tuple[MdictResourceFile, dict[str, dict[str, tuple[int, str]]]] | None:
    global _resource, _index
    if _resource is not None and _index is not None:
        return _resource, _index
    with _lock:
        if _resource is None:
            path = Path(settings.longman_mdd_path)
            if not path.exists():
                return None
            resource = MdictResourceFile(path)
            index: dict[str, dict[str, tuple[int, str]]] = {}
            for name in resource.names():
                parsed = parse_clip_name(name)
                if parsed is None:
                    continue
                accent, word, rank = parsed
                current = index.setdefault(word, {}).get(accent)
                if current is None or (rank, len(name)) < (current[0], len(current[1])):
                    index[word][accent] = (rank, name)
            _resource, _index = resource, index
    return _resource, _index


def is_available() -> bool:
    return Path(settings.longman_mdd_path).exists()


def find_clip(word: str, accent: str = "gb") -> str | None:
    loaded = _load()
    if loaded is None:
        return None
    _, index = loaded
    clips = index.get(word.strip().lower())
    if not clips:
        return None
    preferred = clips.get(accent) or next((clips[a] for a in ACCENTS if a in clips), None)
    return preferred[1] if preferred else None


@lru_cache(maxsize=512)
def get_word_audio_wav(word: str, accent: str = "gb") -> bytes | None:
    """WAV bytes of the Longman pronunciation, or None when the word has no clip."""
    clip = find_clip(word, accent)
    if clip is None:
        return None
    resource, _ = _load()  # type: ignore[misc]
    data = resource.get(clip)
    return speex_to_wav(data) if data else None


def warm_up() -> None:
    """Build the clip index and load the audio decoder ahead of the first click.

    Cold, these take ~1.4 s (index ~0.9 s, PyAV import + first decode ~0.5 s); the app
    calls this in a background thread at startup so the first pronunciation is instant.
    """
    try:
        if not is_available():
            return
        get_word_audio_wav("hello", "gb")
    except Exception:  # noqa: BLE001 - warm-up is best effort; requests still work lazily
        pass


def speex_to_wav(data: bytes) -> bytes:
    """Ogg/Speex -> 16-bit mono WAV.

    Uses the libspeex decoder explicitly: FFmpeg's built-in "speex" decoder (PyAV's
    default) mis-decodes these LDOCE clips (values far outside [-1, 1], NaNs, double
    length), which is heard as loud crackling. libspeex returns clean s16 samples.
    """
    import av  # imported lazily: only needed when audio is actually requested

    with av.open(io.BytesIO(data)) as container:
        stream = container.streams.audio[0]
        rate = stream.codec_context.sample_rate or stream.rate or 22050
        decoder = av.CodecContext.create("libspeex", "r")
        decoder.extradata = stream.codec_context.extradata
        decoder.sample_rate = rate
        decoder.layout = "mono"
        resampler = av.AudioResampler(format="s16", layout="mono", rate=rate)
        pcm = bytearray()
        for packet in container.demux(stream):
            if packet.size == 0:
                continue  # end-of-stream marker; libspeex has nothing buffered to flush
            for frame in decoder.decode(packet):
                for converted in resampler.resample(frame):
                    pcm += converted.to_ndarray().tobytes()
        for converted in resampler.resample(None):
            pcm += converted.to_ndarray().tobytes()

    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(bytes(pcm))
    return output.getvalue()
