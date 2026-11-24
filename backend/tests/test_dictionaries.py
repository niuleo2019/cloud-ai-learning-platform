"""Imported MDict dictionaries: the file reader (with generated .mdx/.mdd files) and the library service."""
import io
import struct
import time
import zlib

import pytest

from app.application.services.dictionary_library_service import DictionaryLibraryService
from app.infrastructure.dictionary import lzo
from app.infrastructure.dictionary.dictionary_files import DictionaryFiles, mdd_files_for
from app.infrastructure.dictionary.mdict import MddFile, MdictError, MdxFile, ripemd128
from app.interfaces.exceptions import AppException

# ------------------------------------------------------------------ a tiny MDict writer for tests


def _zlib_block(data: bytes) -> bytes:
    return b"\x02\x00\x00\x00" + struct.pack(">I", zlib.adler32(data)) + zlib.compress(data)


def _encrypt_key_block_info(block: bytes) -> bytes:
    key = ripemd128(block[4:8] + struct.pack("<L", 0x3695))
    out = bytearray()
    previous = 0x36
    for i, plain in enumerate(block[8:]):
        value = plain ^ previous ^ (i & 0xFF) ^ key[i % len(key)]
        cipher = ((value >> 4) | (value << 4)) & 0xFF
        out.append(cipher)
        previous = cipher
    return block[:8] + bytes(out)


def build_mdict(
    entries: list[tuple[str, bytes]],
    *,
    resource: bool = False,
    version: str = "2.0",
    encrypted: int = 0,
    title: str = "Test Dictionary",
    stylesheet: str = "",
) -> bytes:
    """Write a minimal but valid MDict file: one key block, one record block, zlib compression."""
    v2 = version.startswith("2")
    num = ">Q" if v2 else ">I"
    encoding = "utf-16le" if resource else "utf-8"
    null = b"\x00\x00" if resource else b"\x00"
    entries = sorted(entries, key=lambda item: item[0].lower())

    attrs = f'GeneratedByEngineVersion="{version}" Encrypted="{encrypted}" Title="{title}"'
    if not resource:
        attrs += ' Encoding="UTF-8" KeyCaseSensitive="No"'
        if stylesheet:
            attrs += f' StyleSheet="{stylesheet}"'
    header = f"<{'Library_Data' if resource else 'Dictionary'} {attrs}/>\r\n\x00".encode("utf-16le")
    out = struct.pack(">I", len(header)) + header + struct.pack("<I", zlib.adler32(header))

    records = b""
    key_block = b""
    for key, record in entries:
        key_block += struct.pack(num, len(records)) + key.encode(encoding) + null
        records += record

    first, last = entries[0][0], entries[-1][0]
    compressed_keys = _zlib_block(key_block)
    info = struct.pack(num, len(entries))
    for edge in (first, last):
        text = edge.encode(encoding)
        chars = len(edge)
        if v2:
            info += struct.pack(">H", chars) + text + null
        else:
            info += struct.pack(">B", chars) + text
    info += struct.pack(num, len(compressed_keys)) + struct.pack(num, len(key_block))

    if v2:
        info_block = _zlib_block(info)
        if encrypted & 2:
            info_block = _encrypt_key_block_info(info_block)
        head = struct.pack(">5Q", 1, len(entries), len(info), len(info_block), len(compressed_keys))
        out += head + struct.pack(">I", zlib.adler32(head)) + info_block + compressed_keys
    else:
        out += struct.pack(">4I", 1, len(entries), len(info), len(compressed_keys)) + info + compressed_keys

    compressed_records = _zlib_block(records)
    char = num[1]
    out += struct.pack(">" + char * 4, 1, len(entries), 2 * (8 if v2 else 4), len(compressed_records))
    out += struct.pack(">" + char * 2, len(compressed_records), len(records)) + compressed_records
    return out


ENTRIES = [
    ("abandon", b"<b>abandon</b> to leave <a href='entry://abandonment'>more</a> <img src='snd_uk.png'>\x00"),
    ("Abandonment", b"<b>abandonment</b> the act of leaving\x00"),
    ("colour", b"<b>colour</b> red, blue\x00"),
    ("color", b"@@@LINK=colour\x00"),
    ("well-known", b"<b>well-known</b> famous\x00"),
]


def write(tmp_path, name, data):
    path = tmp_path / name
    path.write_bytes(data)
    return path


# ------------------------------------------------------------------ reader


@pytest.mark.parametrize("version, encrypted", [("2.0", 0), ("2.0", 2), ("1.2", 0)])
def test_mdx_lookup_across_versions_and_encryption(tmp_path, version, encrypted):
    mdx = MdxFile(write(tmp_path, "t.mdx", build_mdict(ENTRIES, version=version, encrypted=encrypted)))
    assert mdx.entry_count == 5
    assert mdx.title == "Test Dictionary"
    assert mdx.lookup("ABANDON")[0].startswith("<b>abandon</b>")
    assert mdx.lookup("abandonment") == ["<b>abandonment</b> the act of leaving"]
    assert mdx.lookup("missing") == []


def test_link_redirect_and_stripped_keys(tmp_path):
    mdx = MdxFile(write(tmp_path, "t.mdx", build_mdict(ENTRIES)))
    assert mdx.lookup("color") == ["<b>colour</b> red, blue"]  # @@@LINK followed
    assert mdx.lookup("wellknown") == ["<b>well-known</b> famous"]  # punctuation-insensitive fallback
    assert mdx.suggest("aban") == ["abandon", "Abandonment"]


def test_stylesheet_markers_are_expanded(tmp_path):
    styles = "1\n&lt;b&gt;\n&lt;/b&gt;\n2\n&lt;i&gt;\n&lt;/i&gt;"
    mdx = MdxFile(write(tmp_path, "s.mdx", build_mdict([("x", b"`1`bold`2`italic\x00")], stylesheet=styles)))
    assert mdx.lookup("x") == ["<b>bold</b><i>italic</i>"]


def test_mdd_resources_with_utf16_keys(tmp_path):
    mdd = MddFile(write(tmp_path, "t.mdd", build_mdict([("\\snd_uk.png", b"PNGDATA"), ("\\css\\a.css", b"body{}")], resource=True)))
    assert mdd.get("snd_uk.png") == b"PNGDATA"
    assert mdd.get("/CSS/A.css") == b"body{}"
    assert mdd.get("nope.png") is None


def test_registered_copies_are_rejected(tmp_path):
    with pytest.raises(MdictError):
        MdxFile(write(tmp_path, "r.mdx", build_mdict(ENTRIES, encrypted=1)))


def test_lzo_block_from_real_lzop_output():
    compressed = bytes.fromhex(
        "00433c623e686172626f75723c2f623e20616e2061726561206f66207761746572206e65787420746f20746865206c616e"
        "642077686572652073686970732063616e207374617920736166656c792e203c623e6861726220006034010002693e5379"
        "646e657920486172626f75723c2f693e110000"
    )
    expected = (b"<b>harbour</b> an area of water next to the land where ships can stay safely. " * 6) + b"<i>Sydney Harbour</i>"
    assert lzo.decompress(compressed, len(expected)) == expected


def test_mdd_files_follow_split_naming(tmp_path):
    for name in ["Oxford.mdx", "Oxford.mdd", "Oxford.2.mdd", "Oxford.1.mdd", "other.mdd"]:
        (tmp_path / name).write_bytes(b"")
    assert mdd_files_for(tmp_path / "Oxford.mdx") == ["Oxford.mdd", "Oxford.1.mdd", "Oxford.2.mdd"]


# ------------------------------------------------------------------ service


class FakeRepository:
    def __init__(self):
        self.rows = {}

    def list_all(self):
        return sorted((dict(r) for r in self.rows.values()), key=lambda r: (r["sort_order"], r["id"]))

    def find_by_id(self, dictionary_id):
        row = self.rows.get(dictionary_id)
        return dict(row) if row else None

    def create(self, payload):
        new_id = len(self.rows) + 1
        self.rows[new_id] = {"id": new_id, "enabled": True, "sort_order": new_id, **payload}
        return dict(self.rows[new_id])

    def update(self, dictionary_id, fields):
        self.rows[dictionary_id].update({k: v for k, v in fields.items() if k in ("title", "enabled", "sort_order")})
        return dict(self.rows[dictionary_id])

    def set_order(self, ordered_ids):
        for position, dictionary_id in enumerate(ordered_ids, start=1):
            self.rows[dictionary_id]["sort_order"] = position

    def delete(self, dictionary_id):
        return self.rows.pop(dictionary_id, None) is not None


def make_service(tmp_path):
    root = tmp_path / "dictionaries"
    root.mkdir()
    return DictionaryLibraryService(FakeRepository(), DictionaryFiles(root), secret="s3cret", max_upload_bytes=10_000_000)


def upload(service, *files):
    return service.import_files(7, [(name, io.BytesIO(data)) for name, data in files])


def test_import_lookup_and_signed_resources(tmp_path):
    service = make_service(tmp_path)
    created = upload(
        service,
        ("My Dict.mdx", build_mdict(ENTRIES)),
        ("My Dict.mdd", build_mdict([("\\snd_uk.png", b"PNG")], resource=True)),
        ("style.css", b"b{color:red}"),
    )
    assert created[0]["title"] == "Test Dictionary" and created[0]["mdd_files"] == ["My Dict.mdd"]

    result = service.lookup("abandon")
    hit = result["results"][0]
    assert hit["found"] and "entry://abandonment" in hit["entries"][0]

    token = hit["resource_base"].rstrip("/").split("/")[-1]
    assert service.resource(1, token, "snd_uk.png") == (b"PNG", "image/png")
    assert service.resource(1, token, "style.css")[0] == b"b{color:red}"  # loose file next to the .mdx
    with pytest.raises(AppException):
        service.resource(1, token, "../../secret.txt")
    with pytest.raises(AppException):
        service.resource(1, "123-bad", "snd_uk.png")
    expired = int(time.time()) - 10
    with pytest.raises(AppException):
        service.resource(1, f"{expired}-{service._sign(1, expired)}", "snd_uk.png")


def test_import_rejects_packages_without_mdx_or_with_odd_files(tmp_path):
    service = make_service(tmp_path)
    with pytest.raises(AppException):
        upload(service, ("only.mdd", b"x"))
    with pytest.raises(AppException):
        upload(service, ("a.mdx", build_mdict(ENTRIES)), ("run.exe", b"x"))
    with pytest.raises(AppException):
        upload(service, ("broken.mdx", b"not a dictionary"))
    assert list((tmp_path / "dictionaries").iterdir()) == []  # failed imports leave nothing behind


def test_scan_registers_copied_folders_and_loose_files(tmp_path):
    service = make_service(tmp_path)
    root = tmp_path / "dictionaries"
    (root / "oxford").mkdir()
    (root / "oxford" / "Oxford.mdx").write_bytes(build_mdict(ENTRIES, title="Oxford"))
    (root / "Loose.mdx").write_bytes(build_mdict(ENTRIES, title="Loose"))
    (root / "Loose.mdd").write_bytes(build_mdict([("\\a.png", b"A")], resource=True))

    result = service.scan(7)
    assert sorted(d["title"] for d in result["added"]) == ["Loose", "Oxford"]
    loose = next(d for d in result["added"] if d["title"] == "Loose")
    assert loose["mdd_files"] == ["Loose.mdd"]
    assert service.scan(7)["added"] == []  # idempotent


def test_disable_reorder_and_delete(tmp_path):
    service = make_service(tmp_path)
    upload(service, ("a.mdx", build_mdict(ENTRIES, title="A")))
    upload(service, ("b.mdx", build_mdict(ENTRIES, title="B")))

    service.update(1, None, False)
    assert [r["title"] for r in service.lookup("abandon")["results"]] == ["B"]

    assert [d["id"] for d in service.reorder([2, 1])] == [2, 1]
    with pytest.raises(AppException):
        service.reorder([1])

    folder = tmp_path / "dictionaries" / service.repository.rows[2]["folder"]
    service.delete(2)
    assert not folder.exists()


def test_examples_with_audio_pairs_sound_links_with_sentences(tmp_path):
    from app.infrastructure.dictionary.dictionary_files import examples_with_audio

    html = (
        '<a href="sound://p008__1.spx"><img src="snd_sfx.png"></a> <ex><font>At present we have no '
        'evidence of life on other planets.</font></ex><br>'
        '<a href="sound://p008__2.spx" ><img></a> <ex>Too short</ex>'
    )
    assert examples_with_audio(html) == [("At present we have no evidence of life on other planets.", "p008__1.spx")]
    # headword audio followed later by an example must not steal the example (regression)
    html = '<a href="sound://GB_evidence.spx"><img></a> noun <b>evidence of</b><br> <a href="sound://p9.spx"><img></a> <ex>We have no evidence of that.</ex>'
    assert examples_with_audio(html) == [("We have no evidence of that.", "p9.spx")]


def test_service_examples_come_from_dictionary_with_resources(tmp_path):
    service = make_service(tmp_path)
    entry = b'<a href="sound://p1.spx"><img></a> <ex>There is no evidence for these claims.</ex>\x00'
    upload(
        service,
        ("Ex.mdx", build_mdict([("evidence", entry)])),
        ("Ex.mdd", build_mdict([("\p1.spx", b"SPX")], resource=True)),
    )
    result = service.examples("Evidence")
    assert result["examples"] == [{"text": "There is no evidence for these claims.", "audio": "p1.spx"}]
    assert result["resource_base"].startswith("/dictionaries/1/res/")
