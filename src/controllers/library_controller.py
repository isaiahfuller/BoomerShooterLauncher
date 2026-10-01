"""Coordinate record-backed runner/version choices without accessing widgets."""
from PySide6 import QtCore

from models.records import Modpack


class LibraryController(QtCore.QObject):
    choices_changed = QtCore.Signal(object, object, object)

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository

    def select(self, record):
        """Publish compatible choices from one snapshot and remembered identities."""
        if record is None:
            self.choices_changed.emit(None, (), ())
            return
        is_modpack = isinstance(record, Modpack)
        family = record.base if is_modpack else record.family
        runner, version = self.repository.last_selection(record.name, modpack=is_modpack)
        library = self.repository.library()
        runners = library.compatible_runners(family, preferred=runner)
        versions = library.installed_versions(record.name, modpack=is_modpack,
                                              preferred=version)
        self.choices_changed.emit(record, runners, versions)
