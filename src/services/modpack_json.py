"""Portable modpack JSON boundary; local paths are deliberately not exported."""
import json

from models.records import ModFile, Modpack


def decode_modpack(data):
    """Validate portable metadata and return an unresolved, ordered draft."""
    if not isinstance(data, dict):
        raise ValueError("Modpack JSON must be an object")
    if not isinstance(data.get("name"), str) or not data["name"]:
        raise ValueError("Modpack name must be a non-empty string")
    if not isinstance(data.get("base"), str):
        raise ValueError("Modpack base must be a string")
    if not isinstance(data.get("mods"), list):
        raise ValueError("Modpack mods must be a list")
    files = []
    for entry in data["mods"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise ValueError("Each mod must have a string name")
        if not isinstance(entry.get("source"), str):
            raise ValueError("Each mod must have a string source")
        files.append(ModFile(entry["name"], None, entry["source"]))
    return Modpack(data["name"], data["base"], tuple(files))


def read_modpack(path):
    with open(path, encoding="utf-8") as stream:
        return decode_modpack(json.load(stream))


def write_modpack(path, pack):
    data = {"name": pack.name, "base": pack.base,
            "mods": [{"name": file.name, "source": file.source} for file in pack.files]}
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=4)
