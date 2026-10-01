"""Coordinate modpack drafts, file resolution, and persistence without widgets."""
import os
from dataclasses import replace

from PySide6 import QtCore

from models.records import ModFile, Modpack
from services.modpack_json import decode_modpack, read_modpack, write_modpack


class ModpackController(QtCore.QObject):
    failed = QtCore.Signal(str)
    saved = QtCore.Signal()

    def __init__(self, repository, parent=None, *, draft=None):
        super().__init__(parent)
        self.repository = repository
        # Legacy dialog callers may still supply portable import metadata.
        if isinstance(draft, dict):
            draft = decode_modpack(draft)
        self.draft = draft if draft is not None else Modpack("Mod name", "", ())
        self.original_name = None

    def bases(self):
        return sorted({game.family for game in self.repository.library().games if game.family})

    def open(self, record):
        self.draft = next(pack for pack in self.repository.library().modpacks
                          if pack.name == record.name)
        self.original_name = self.draft.name
        return self.draft

    def load_json(self, path):
        try:
            draft = read_modpack(path)
        except (OSError, ValueError) as error:
            self.failed.emit(str(error))
            return None
        self.draft = draft
        self.original_name = None
        return draft

    def export_json(self, path):
        try:
            write_modpack(path, self.draft)
        except (OSError, ValueError, TypeError) as error:
            self.failed.emit(str(error))
            return False
        return True

    def change(self, **changes):
        self.draft = replace(self.draft, **changes)

    def change_file(self, row, **changes):
        if not 0 <= row < len(self.draft.files):
            return False
        files = list(self.draft.files)
        files[row] = replace(files[row], **changes)
        self.change(files=tuple(files))
        return True

    def add_file(self, path):
        if any(file.path == path for file in self.draft.files):
            return False
        self.change(files=self.draft.files + (ModFile(os.path.basename(path), path, ""),))
        return True

    def remove_file(self, row):
        if not 0 <= row < len(self.draft.files):
            return None
        self.change(files=self.draft.files[:row] + self.draft.files[row + 1:])
        return min(row, len(self.draft.files) - 1)

    def move_file(self, row, offset):
        target = row + offset
        if not (0 <= row < len(self.draft.files) and 0 <= target < len(self.draft.files)):
            return None
        files = list(self.draft.files)
        files[row], files[target] = files[target], files[row]
        self.change(files=tuple(files))
        return target

    def resolve_dropped(self, path):
        for row, file in enumerate(self.draft.files):
            if file.name == os.path.basename(path) and file.path is None:
                self.change_file(row, path=path)
                return row
        return None

    @property
    def loaded_count(self):
        return sum(file.path is not None for file in self.draft.files)

    def save(self, *, require_resolved=False):
        if not self.draft.name or (require_resolved and self.loaded_count != len(self.draft.files)):
            return False
        try:
            self.repository.save_modpack_record(self.draft)
            if self.original_name and self.original_name != self.draft.name:
                runner, version = self.repository.last_selection(self.original_name, modpack=True)
                self.repository.save_selection(self.draft.name, runner, version, modpack=True)
                self.repository.remove_modpack(self.original_name)
        except OSError as error:
            self.failed.emit(str(error))
            return False
        self.original_name = self.draft.name
        self.saved.emit()
        return True

    def remove(self, record):
        try:
            self.repository.remove_modpack(record.name)
        except OSError as error:
            self.failed.emit(str(error))
            return False
        return True
