"""Domain records; names retain their existing persisted identities."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InstalledVersion:
    name: str
    version: str | None
    crc: str | None
    path: str | None


@dataclass(frozen=True)
class Game:
    name: str
    family: str | None
    year: str | int | None
    versions: tuple[InstalledVersion, ...]


@dataclass(frozen=True)
class Runner:
    name: str
    path: str | None
    executable: str | None


@dataclass(frozen=True)
class ModFile:
    name: str | None
    path: str | None
    source: str | None


@dataclass(frozen=True)
class Modpack:
    name: str
    base: str | None
    files: tuple[ModFile, ...]
