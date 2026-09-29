"""Read and write the launcher's existing QSettings schema.

Each operation creates its own QSettings instance. Group/array cursors never
escape an operation or get shared between the scanner and the GUI thread.
Pass a factory returning isolated QSettings instances when testing.
"""

from contextlib import contextmanager
import platform

from PySide6 import QtCore


def create_settings():
    """Keep the historical native-format settings locations unchanged."""
    system = platform.system()
    if system == "Windows":
        return QtCore.QSettings("Isaiah Fuller", "Boomer Shooter Launcher")
    if system == "Linux":
        return QtCore.QSettings("boomershooterlauncher", "config")
    raise RuntimeError(f"Unsupported settings platform: {system}")


class SettingsRepository:
    """Persist library records independently of widgets and presentation."""

    def __init__(self, settings_factory=None):
        self._settings_factory = settings_factory or create_settings

    @contextmanager
    def _session(self, group, *, write=False):
        settings = self._settings_factory()
        settings.beginGroup(group)
        try:
            yield settings
        finally:
            settings.endGroup()
            if write:
                settings.sync()
                if settings.status() != QtCore.QSettings.NoError:
                    raise OSError(f"Unable to save settings: {settings.fileName()}")

    def library(self):
        """Translate legacy settings into domain records without changing storage."""
        from models.library import Library
        from models.records import Game, InstalledVersion, ModFile, Modpack, Runner

        games = tuple(
            Game(name, record["game"], record["year"], tuple(
                InstalledVersion(release_name, **release)
                for release_name, release in record["releases"].items()
            ))
            for name, record in self.games().items()
        )
        runners = tuple(Runner(name, **record) for name, record in self.runners().items())
        modpacks = tuple(
            Modpack(name, record["base"], tuple(ModFile(**file) for file in record["files"]))
            for name, record in self.modpacks().items()
        )
        return Library(games, runners, modpacks)

    def window_geometry(self):
        with self._session("MainWindow") as settings:
            return settings.value("geometry", QtCore.QByteArray())

    def save_window_geometry(self, geometry):
        with self._session("MainWindow", write=True) as settings:
            settings.setValue("geometry", geometry)

    def games(self):
        """Return base names mapped to metadata and installed releases."""
        with self._session("Games") as settings:
            result = {}
            for base in settings.childGroups():
                settings.beginGroup(base)
                try:
                    releases = {}
                    for name in settings.childGroups():
                        releases[name] = {
                            key: settings.value(f"{name}/{key}")
                            for key in ("version", "crc", "path")
                        }
                    result[base] = {
                        "game": settings.value("game"),
                        "year": settings.value("year"),
                        "version": settings.value("version"),
                        "releases": releases,
                    }
                finally:
                    settings.endGroup()
            return result

    def save_game(self, base, name, *, version, crc, path, year, game):
        with self._session(f"Games/{base}", write=True) as settings:
            for key, value in (("version", version), ("crc", crc), ("path", path)):
                settings.setValue(f"{name}/{key}", value)
            settings.setValue("year", year)
            settings.setValue("game", game)

    def runners(self):
        with self._session("Runners") as settings:
            return {
                name: {key: settings.value(f"{name}/{key}")
                       for key in ("path", "executable")}
                for name in settings.childGroups()
            }

    def save_runner(self, name, path, executable):
        with self._session(f"Runners/{name}", write=True) as settings:
            settings.setValue("path", path)
            settings.setValue("executable", executable)

    def remove_runner(self, name):
        with self._session("Runners", write=True) as settings:
            settings.remove(name)

    def modpacks(self):
        with self._session("Modpacks") as settings:
            result = {}
            for name in settings.childGroups():
                settings.beginGroup(name)
                try:
                    base = settings.value("base")
                    files = []
                    size = settings.beginReadArray("files")
                    try:
                        for index in range(size):
                            settings.setArrayIndex(index)
                            files.append({key: settings.value(key)
                                          for key in ("name", "path", "source")})
                    finally:
                        settings.endArray()
                    result[name] = {"name": name, "base": base, "files": files}
                finally:
                    settings.endGroup()
            return result

    def save_modpack(self, name, base, files):
        with self._session(f"Modpacks/{name}", write=True) as settings:
            settings.setValue("base", base)
            # Clear obsolete entries when a pack shrinks, including to zero.
            settings.remove("files")
            settings.beginWriteArray("files", len(files))
            try:
                for index, file in enumerate(files):
                    settings.setArrayIndex(index)
                    for key in ("name", "path", "source"):
                        settings.setValue(key, file[key])
            finally:
                settings.endArray()

    def save_modpack_record(self, pack):
        """Persist an immutable draft using the existing array schema."""
        from dataclasses import asdict
        self.save_modpack(pack.name, pack.base, [asdict(file) for file in pack.files])

    def remove_modpack(self, name):
        with self._session("Modpacks", write=True) as settings:
            settings.remove(name)

    def last_selection(self, name, *, modpack=False):
        group = "Modpacks" if modpack else "Games"
        with self._session(f"{group}/{name}") as settings:
            return settings.value("Last Runner"), settings.value("Last Version")

    def save_selection(self, name, runner, version, *, modpack=False):
        group = "Modpacks" if modpack else "Games"
        with self._session(f"{group}/{name}", write=True) as settings:
            settings.setValue("Last Runner", runner)
            settings.setValue("Last Version", version)
