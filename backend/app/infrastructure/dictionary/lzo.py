"""Pure-Python LZO1X decompressor (the 'type 1' compression used by older MDict files).

python-lzo has no wheels for this platform, and MDict blocks are small (tens of KB),
so a straightforward port of lzo1x_decompress_safe is fast enough.
"""
from __future__ import annotations


class LzoError(ValueError):
    pass


def decompress(src: bytes, expected_size: int | None = None) -> bytes:
    out = bytearray()
    ip = 0
    n = len(src)

    def byte() -> int:
        nonlocal ip
        if ip >= n:
            raise LzoError("LZO input overrun")
        value = src[ip]
        ip += 1
        return value

    def extended(base: int) -> int:
        """Length with zero-byte extensions: each 0 adds 255."""
        length = 0
        while True:
            value = byte()
            if value:
                return length + base + value
            length += 255

    def copy_literals(count: int) -> None:
        nonlocal ip
        if ip + count > n:
            raise LzoError("LZO literal overrun")
        out.extend(src[ip : ip + count])
        ip += count

    def copy_match(distance: int, count: int) -> None:
        start = len(out) - distance
        if start < 0:
            raise LzoError("LZO lookbehind overrun")
        if distance >= count:
            out.extend(out[start : start + count])
        else:  # overlapping copy repeats the pattern
            for i in range(count):
                out.append(out[start + i])

    state = "loop"
    t = byte()
    if t > 17:
        t -= 17
        if t < 4:
            state = "match_next"  # match_next copies these literals itself
        else:
            copy_literals(t)
            state = "first_literal_run"
    else:
        ip -= 1

    while True:
        if state == "loop":
            t = byte()
            if t >= 16:
                state = "match"
                continue
            if t == 0:
                t = extended(15)
            copy_literals(t + 3)
            state = "first_literal_run"
            continue

        if state == "first_literal_run":
            t = byte()
            if t >= 16:
                state = "match"
                continue
            # 3-byte match just beyond the M2 range
            distance = 1 + 0x0800 + (t >> 2) + (byte() << 2)
            copy_match(distance, 3)
            state = "match_done"
            continue

        if state == "match":
            if t >= 64:  # M2: 3-8 bytes, distance <= 2048
                distance = 1 + ((t >> 2) & 7) + (byte() << 3)
                copy_match(distance, (t >> 5) + 1)
            elif t >= 32:  # M3: distance <= 16384
                length = t & 31
                if length == 0:
                    length = extended(31)
                low, high = byte(), byte()
                distance = 1 + ((low | (high << 8)) >> 2)
                copy_match(distance, length + 2)
            elif t >= 16:  # M4: distance 16385..49151, or end of stream
                high_bit = (t & 8) << 11
                length = t & 7
                if length == 0:
                    length = extended(7)
                low, high = byte(), byte()
                distance = high_bit + ((low | (high << 8)) >> 2)
                if distance == 0:
                    break  # end-of-stream marker
                copy_match(distance + 0x4000, length + 2)
            else:  # M1: 2-byte match after a match
                distance = 1 + (t >> 2) + (byte() << 2)
                copy_match(distance, 2)
            state = "match_done"
            continue

        if state == "match_done":
            t = src[ip - 2] & 3
            if t == 0:
                state = "loop"
                continue
            state = "match_next"
            continue

        if state == "match_next":
            copy_literals(t)
            t = byte()
            state = "match"
            continue

    if expected_size is not None and len(out) != expected_size:
        raise LzoError(f"LZO size mismatch: got {len(out)}, expected {expected_size}")
    return bytes(out)
