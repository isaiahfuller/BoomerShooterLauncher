"""Choose game files and coordinate background directory scans."""

import logging
import os

from PySide6 import QtCore

from repositories.settings_repository import SettingsRepository
from services.game_files import scan_game_file

FILE_TYPES = (".wad", ".pk3", ".ipk3")


class DirectoryScanWorker(QtCore.QThread):
    """Scan files without touching widgets from the worker thread."""

    progress = QtCore.Signal(str)

    def __init__(self, directory, parent=None, *, repository=None):
        super().__init__(parent)
        self.directory = directory
        self.repository = repository

    def run(self):
        repository = (
            self.repository if self.repository is not None else SettingsRepository()
        )
        logger = logging.getLogger("Game Scanner")
        entries = (
            os.walk(self.directory)
            if os.path.isdir(self.directory)
            else [
                (
                    os.path.dirname(self.directory),
                    [],
                    [os.path.basename(self.directory)],
                )
            ]
        )
        for parent, _, names in entries:
            if self.isInterruptionRequested():
                return
            for name in names:
                if self.isInterruptionRequested():
                    return
                if not name.lower().endswith(FILE_TYPES):
                    continue
                path = os.path.realpath(os.path.join(parent, name))
                self.progress.emit(f"Scanning games... ({path})")
                try:
                    scan_game_file(path, repository, self.isInterruptionRequested)
                except (OSError, ValueError):
                    logger.exception("Failed to scan file %s", path)

