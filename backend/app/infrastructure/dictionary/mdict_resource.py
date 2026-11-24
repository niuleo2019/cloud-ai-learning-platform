"""Backwards-compatible names for the .mdd reader (the implementation lives in mdict.py)."""
from app.infrastructure.dictionary.mdict import MddFile as MdictResourceFile
from app.infrastructure.dictionary.mdict import normalise_resource_name, ripemd128

__all__ = ["MdictResourceFile", "normalise_resource_name", "ripemd128"]
