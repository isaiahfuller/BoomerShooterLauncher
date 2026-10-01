"""Coordinate runner configuration without depending on widgets."""
import os
from pathlib import Path
import shutil

from PySide6 import QtCore

from models.catalog import runners
from models.records import Runner


class RunnerController(QtCore.QObject):
    failed = QtCore.Signal(str, str)
    saved = QtCore.Signal(object)
    removed = QtCore.Signal()

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.clear()

    def clear(self):
        self.name = None
        self.executable = None
        self.url = None
        self.description = ""
        self.path = ""
        self.installed = False
        self.custom = False

    def choices(self, game):
        """Return records and installation flags; the view adds its custom entry."""
        if game == "all":
            installed = self.repository.library().runners
            names = {record.name for record in installed}
            return tuple((record, True) for record in installed) + tuple(
                (Runner(name, None, metadata["executable"]), False)
                for name, metadata in runners.items() if name not in names)
        return tuple((Runner(name, None, metadata["executable"]), False)
                     for name, metadata in runners.items() if game in metadata["games"])

    def select(self, record, *, custom=False):
        self.clear()
        if record is None and not custom:
            return
        self.custom = custom
        self.name = "Custom..." if custom else record.name
        saved = None if custom else next(
            (runner for runner in self.repository.library().runners
             if runner.name == record.name), None)
        self.installed = saved is not None
        if custom:
            self.executable = "*"
            self.description = "Add a runner that isn't listed."
        elif self.name in runners:
            metadata = runners[self.name]
            self.executable = metadata["executable"]
            self.description = metadata["description"]
            self.url = metadata["link"]
        else:
            self.executable = saved.executable if saved else record.executable
            self.description = "Custom runner."
        detected = shutil.which(self.executable) if self.executable != "*" else None
        self.path = (saved.path or "") if saved else (detected or "")

    def change_path(self, path):
        self.path = path

    @property
    def can_save(self):
        return self.name is not None and bool(self.path)

    def save(self):
        if not self.can_save:
            return None
        path = Path(self.path).expanduser()
        if not path.is_file() or not os.access(path, os.X_OK):
            self.failed.emit("Invalid program", "Choose an existing executable file.")
            return None
        name = path.name if self.custom else self.name
        record = Runner(name, str(path.absolute()), self.executable)
        try:
            self.repository.save_runner(record.name, record.path, record.executable)
        except OSError as error:
            self.failed.emit("Unable to save runner", str(error))
            return None
        self.saved.emit(record)
        return record

    def remove(self):
        if not self.installed or self.custom:
            return False
        try:
            self.repository.remove_runner(self.name)
        except OSError as error:
            self.failed.emit("Unable to remove runner", str(error))
            return False
        self.clear()
        self.removed.emit()
        return True
