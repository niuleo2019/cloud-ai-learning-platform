"""Random-access reader for MDict dictionaries: .mdx (entries) and .mdd (resources).

Supports engine versions 1.x and 2.x, UTF-8 / GBK / UTF-16 keys, the common
"Encrypted=2" key-index encryption, and zlib / LZO / uncompressed blocks.
Opening a file reads only the key index (a second or less for big dictionaries);
each lookup then reads and decompresses one record block.

Not supported: "Encrypted=1" files that need a registration key (user-bound copies).
"""
from __future__ import annotations

import bisect
import html
import re
import struct
import threading
import zlib
from collections import OrderedDict
from pathlib import Path

from app.infrastructure.dictionary import lzo

# ---------------------------------------------------------------- RIPEMD-128 (key-index decryption)

_R = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    7, 4, 13, 1, 10, 6, 15, 3, 12, 0, 9, 5, 2, 14, 11, 8,
    3, 10, 14, 4, 9, 15, 8, 1, 2, 7, 0, 6, 13, 11, 5, 12,
    1, 9, 11, 10, 0, 8, 12, 4, 13, 3, 7, 15, 14, 5, 6, 2,
]
_RP = [
    5, 14, 7, 0, 9, 2, 11, 4, 13, 6, 15, 8, 1, 10, 3, 12,
    6, 11, 3, 7, 0, 13, 5, 10, 14, 15, 8, 12, 4, 9, 1, 2,
    15, 5, 1, 3, 7, 14, 6, 9, 11, 8, 12, 2, 10, 0, 4, 13,
    8, 6, 4, 1, 3, 11, 15, 0, 5, 12, 2, 13, 9, 7, 10, 14,
]
_S = [
    11, 14, 15, 12, 5, 8, 7, 9, 11, 13, 14, 15, 6, 7, 9, 8,
    7, 6, 8, 13, 11, 9, 7, 15, 7, 12, 15, 9, 11, 7, 13, 12,
    11, 13, 6, 7, 14, 9, 13, 15, 14, 8, 13, 6, 5, 12, 7, 5,
    11, 12, 14, 15, 14, 15, 9, 8, 9, 14, 5, 6, 8, 6, 5, 12,
]
_SP = [
    8, 9, 9, 11, 13, 15, 15, 5, 7, 7, 8, 11, 14, 14, 12, 6,
    9, 13, 15, 7, 12, 8, 9, 11, 7, 7, 12, 7, 6, 15, 13, 11,
    9, 7, 15, 11, 8, 6, 6, 14, 12, 13, 5, 14, 13, 13, 7, 5,
    15, 5, 8, 11, 14, 14, 6, 14, 6, 9, 12, 9, 12, 5, 15, 8,
]
_MASK = 0xFFFFFFFF


def _f(j: int, x: int, y: int, z: int) -> int:
    if j < 16:
        return x ^ y ^ z
    if j < 32:
        return (x & y) | (z & ~x & _MASK)
    if j < 48:
        return (x | (~y & _MASK)) ^ z
    return (x & z) | (y & ~z & _MASK)


def _rol(s: int, x: int) -> int:
    return ((x << s) | (x >> (32 - s))) & _MASK


def ripemd128(message: bytes) -> bytes:
    length = len(message)
    message = message + b"\x80" + b"\x00" * ((55 - length) % 64) + struct.pack("<Q", length * 8)
    h0, h1, h2, h3 = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476
    k = (0x00000000, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC)
    kp = (0x50A28BE6, 0x5C4DD124, 0x6D703EF3, 0x00000000)
    for offset in range(0, len(message), 64):
        x = struct.unpack("<16L", message[offset : offset + 64])
        a, b, c, d = h0, h1, h2, h3
        ap, bp, cp, dp = h0, h1, h2, h3
        for j in range(64):
            t = _rol(_S[j], (a + _f(j, b, c, d) + x[_R[j]] + k[j // 16]) & _MASK)
            a, d, c, b = d, c, b, t
            t = _rol(_SP[j], (ap + _f(63 - j, bp, cp, dp) + x[_RP[j]] + kp[j // 16]) & _MASK)
            ap, dp, cp, bp = dp, cp, bp, t
        t = (h1 + c + dp) & _MASK
        h1 = (h2 + d + ap) & _MASK
        h2 = (h3 + a + bp) & _MASK
        h3 = (h0 + b + cp) & _MASK
        h0 = t
    return struct.pack("<4L", h0, h1, h2, h3)


def _decrypt_key_block_info(block: bytes) -> bytes:
    key = ripemd128(block[4:8] + struct.pack("<L", 0x3695))
    data = bytearray(block[8:])
    previous = 0x36
    for i, value in enumerate(data):
        swapped = ((value >> 4) | (value << 4)) & 0xFF
        data[i] = swapped ^ previous ^ (i & 0xFF) ^ key[i % len(key)]
        previous = value
    return block[:8] + bytes(data)


def _decompress(block: bytes, expected_size: int | None = None) -> bytes:
    kind = block[:4]
    if kind == b"\x00\x00\x00\x00":
        return block[8:]
    if kind == b"\x02\x00\x00\x00":
        return zlib.decompress(block[8:])
    if kind == b"\x01\x00\x00\x00":
        return lzo.decompress(block[8:], expected_size)
    raise MdictError(f"Unknown block compression {kind.hex()}")


class MdictError(ValueError):
    """The file is not a readable MDict dictionary (corrupt, unsupported or registered copy)."""


# ---------------------------------------------------------------- base reader


def normalise_resource_name(name: str) -> str:
    return name.replace("/", "\\").lstrip("\\").lower()


def _python_encoding(name: str) -> str:
    upper = (name or "").upper().replace("-", "")
    if upper in ("", "UTF8"):
        return "utf-8"
    if upper in ("GBK", "GB2312", "GB18030"):
        return "gb18030"
    if upper in ("BIG5",):
        return "big5"
    if upper in ("UTF16", "UTF16LE"):
        return "utf-16le"
    return name


class MdictFile:
    is_resource_file = False

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._block_cache: OrderedDict[int, bytes] = OrderedDict()
        try:
            with self.path.open("rb") as file:
                self._read_header(file)
                keys, offsets = self._read_keys(file)
                self._read_record_info(file)
        except MdictError:
            raise
        except (struct.error, zlib.error, lzo.LzoError, IndexError, UnicodeDecodeError) as error:
            raise MdictError(f"Could not read {self.path.name}: {error}") from error

        # Record lengths come from the next entry's offset (entries are stored in offset order).
        self.entry_count = len(keys)
        self._keys = keys
        self._offsets = offsets
        order = sorted(range(len(offsets)), key=offsets.__getitem__)
        self._sizes = [0] * len(offsets)
        for position, index in enumerate(order):
            end = offsets[order[position + 1]] if position + 1 < len(order) else self._total_size
            self._sizes[index] = end - offsets[index]

    # -- header ----------------------------------------------------------------

    def _read_header(self, file) -> None:
        header_size = struct.unpack(">I", file.read(4))[0]
        header_text = file.read(header_size).decode("utf-16le", errors="ignore")
        file.read(4)  # adler32
        self.header = {name: html.unescape(value) for name, value in re.findall(r'(\w+)="((?:.|\n)*?)"', header_text)}
        try:
            self.version = float(self.header.get("GeneratedByEngineVersion") or "2.0")
        except ValueError:
            self.version = 2.0
        encrypted = self.header.get("Encrypted", "0")
        self.encrypted = 0 if encrypted in ("", "No") else 1 if encrypted == "Yes" else int(encrypted)
        if self.encrypted & 1:
            raise MdictError("This dictionary is registered to a specific user (Encrypted=1) and needs its key")
        self._number_format = ">Q" if self.version >= 2.0 else ">I"
        self._number_width = 8 if self.version >= 2.0 else 4
        if self.is_resource_file:
            self.encoding = "utf-16le"
        else:
            self.encoding = _python_encoding(self.header.get("Encoding", ""))

    def _number(self, data: bytes, pos: int) -> int:
        return struct.unpack(self._number_format, data[pos : pos + self._number_width])[0]

    # -- keys -------------------------------------------------------------------

    def _read_keys(self, file) -> tuple[list[str], list[int]]:
        width = self._number_width
        if self.version >= 2.0:
            head = file.read(width * 5)
            num_blocks, _entries, _info_decomp, info_size, blocks_size = (self._number(head, i * width) for i in range(5))
            file.read(4)  # adler32
        else:
            head = file.read(width * 4)
            num_blocks, _entries, info_size, blocks_size = (self._number(head, i * width) for i in range(4))

        info = file.read(info_size)
        if self.version >= 2.0:
            if self.encrypted & 2:
                info = _decrypt_key_block_info(info)
            info = _decompress(info)

        utf16 = self.encoding == "utf-16le"
        size_format, size_width, terminator = (">H", 2, 1) if self.version >= 2.0 else (">B", 1, 0)
        sizes: list[tuple[int, int]] = []
        pos = 0
        for _ in range(num_blocks):
            pos += width  # entries in this block
            for _edge in range(2):  # first and last key of the block
                (chars,) = struct.unpack(size_format, info[pos : pos + size_width])
                pos += size_width + (chars + terminator) * (2 if utf16 else 1)
            compressed = self._number(info, pos)
            decompressed = self._number(info, pos + width)
            pos += width * 2
            sizes.append((compressed, decompressed))

        data = file.read(blocks_size)
        keys: list[str] = []
        offsets: list[int] = []
        null = b"\x00\x00" if utf16 else b"\x00"
        start = 0
        for compressed, decompressed in sizes:
            block = _decompress(data[start : start + compressed], decompressed)
            start += compressed
            pos = 0
            while pos < len(block):
                offsets.append(self._number(block, pos))
                pos += width
                end = block.find(null, pos)
                if utf16:
                    while end != -1 and (end - pos) % 2:  # align to a UTF-16 code unit
                        end = block.find(null, end + 1)
                if end == -1:
                    end = len(block)
                keys.append(block[pos:end].decode(self.encoding, errors="ignore"))
                pos = end + len(null)
        return keys, offsets

    # -- records ----------------------------------------------------------------

    def _read_record_info(self, file) -> None:
        width = self._number_width
        head = file.read(width * 4)
        num_blocks, _entries, info_size, _blocks_size = (self._number(head, i * width) for i in range(4))
        info = file.read(info_size)
        self._block_file_offsets: list[int] = []
        self._block_compressed: list[int] = []
        self._block_decompressed: list[int] = []
        self._block_starts: list[int] = []
        file_offset = file.tell()
        stream_offset = 0
        for i in range(num_blocks):
            compressed = self._number(info, i * width * 2)
            decompressed = self._number(info, i * width * 2 + width)
            self._block_file_offsets.append(file_offset)
            self._block_compressed.append(compressed)
            self._block_decompressed.append(decompressed)
            self._block_starts.append(stream_offset)
            file_offset += compressed
            stream_offset += decompressed
        self._total_size = stream_offset

    def _record(self, index: int) -> bytes:
        offset, size = self._offsets[index], self._sizes[index]
        chunks = []
        while size > 0:
            block_index = bisect.bisect_right(self._block_starts, offset) - 1
            block = self._block(block_index)
            local = offset - self._block_starts[block_index]
            piece = block[local : local + size]
            if not piece:
                break
            chunks.append(piece)
            offset += len(piece)
            size -= len(piece)
        return b"".join(chunks)

    def _block(self, index: int) -> bytes:
        with self._lock:
            cached = self._block_cache.get(index)
            if cached is not None:
                self._block_cache.move_to_end(index)
                return cached
            with self.path.open("rb") as file:
                file.seek(self._block_file_offsets[index])
                raw = file.read(self._block_compressed[index])
            block = _decompress(raw, self._block_decompressed[index])
            self._block_cache[index] = block
            if len(self._block_cache) > 8:
                self._block_cache.popitem(last=False)
            return block

    @property
    def title(self) -> str:
        title = re.sub(r"<[^>]+>", "", self.header.get("Title", "")).strip()
        return "" if title.lower() in ("", "title (no html code allowed)") else title


# ---------------------------------------------------------------- .mdd resources


class MddFile(MdictFile):
    is_resource_file = True

    def __init__(self, path: str | Path):
        super().__init__(path)
        self._names = {normalise_resource_name(key): index for index, key in enumerate(self._keys)}

    def names(self) -> list[str]:
        return list(self._names)

    def __contains__(self, name: str) -> bool:
        return normalise_resource_name(name) in self._names

    def get(self, name: str) -> bytes | None:
        index = self._names.get(normalise_resource_name(name))
        return None if index is None else self._record(index)


# ---------------------------------------------------------------- .mdx entries


def normalise_headword(word: str) -> str:
    return " ".join(word.strip().lower().split())


def strip_headword(word: str) -> str:
    """For StripKey dictionaries: compare letters and digits only."""
    return re.sub(r"[\W_]+", "", word.lower())


class MdxFile(MdictFile):
    MAX_LINK_DEPTH = 5

    def __init__(self, path: str | Path):
        super().__init__(path)
        self._index: dict[str, list[int]] = {}
        self._stripped: dict[str, list[int]] = {}
        for index, key in enumerate(self._keys):
            self._index.setdefault(normalise_headword(key), []).append(index)
            stripped = strip_headword(key)
            if stripped:
                self._stripped.setdefault(stripped, []).append(index)
        self._sorted_keys = sorted(self._index)
        self._stylesheet = self._parse_stylesheet(self.header.get("StyleSheet", ""))

    @staticmethod
    def _parse_stylesheet(text: str) -> dict[str, tuple[str, str]]:
        lines = text.splitlines()
        styles = {}
        for i in range(0, len(lines) - 2, 3):
            styles[lines[i].strip()] = (lines[i + 1], lines[i + 2])
        return styles

    def _apply_stylesheet(self, text: str) -> str:
        if not self._stylesheet or "`" not in text:
            return text
        parts = re.split(r"`(\d+)`", text)
        styled = parts[0]
        for number, body in zip(parts[1::2], parts[2::2]):
            begin, end = self._stylesheet.get(number, ("", ""))
            styled += f"{begin}{body.rstrip()}{end}\r\n" if body.endswith("\n") else f"{begin}{body}{end}"
        return styled

    def _text(self, index: int) -> str:
        text = self._record(index).decode(self.encoding, errors="replace").rstrip("\x00").strip()
        return self._apply_stylesheet(text)

    def _find(self, word: str) -> list[int]:
        return self._index.get(normalise_headword(word)) or self._stripped.get(strip_headword(word)) or []

    def lookup(self, word: str) -> list[str]:
        """All entries for a headword, following @@@LINK= redirects."""
        results: list[str] = []
        seen: set[int] = set()
        queue = [(index, 0) for index in self._find(word)]
        while queue:
            index, depth = queue.pop(0)
            if index in seen:
                continue
            seen.add(index)
            text = self._text(index)
            if text.startswith("@@@LINK="):
                if depth < self.MAX_LINK_DEPTH:
                    target = text[len("@@@LINK=") :].strip().splitlines()[0].strip()
                    queue.extend((i, depth + 1) for i in self._find(target))
                continue
            results.append(text)
        return results

    def suggest(self, prefix: str, limit: int = 10) -> list[str]:
        key = normalise_headword(prefix)
        if not key:
            return []
        start = bisect.bisect_left(self._sorted_keys, key)
        matches = []
        for candidate in self._sorted_keys[start : start + limit * 3]:
            if not candidate.startswith(key):
                break
            matches.append(self._keys[self._index[candidate][0]])
            if len(matches) >= limit:
                break
        return matches
