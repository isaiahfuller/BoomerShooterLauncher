"""Run Steam discovery and game identification outside the GUI thread."""

import logging
import os

from PySide6 import QtCore

from repositories.settings_repository import SettingsRepository
from services.game_files import scan_game_file
from services.steam import installed_game_directories


class SteamScanner(QtCore.QThread):
    progress = QtCore.Signal(str)
    completed = QtCore.Signal(int, int, int)
    failed = QtCore.Signal(str)

    def __init__(self, parent=None, *, repository=None):
        super().__init__(parent)
        self.repository = repository

    def run(self):
        try:
            directories = installed_game_directories()
            repository = (
                self.repository if self.repository is not None else SettingsRepository()
            )
            found = 0
            errors = 0
            seen = set()

            def walk_error(error):
                nonlocal errors
                errors += 1
                logging.getLogger(__name__).warning("%s", error)

            for directory in directories:
                if self.isInterruptionRequested():
                    return
                self.progress.emit(f"Scanning Steam: {directory.name}")
                for parent, _, files in os.walk(directory, onerror=walk_error):
                    for name in files:
                        if self.isInterruptionRequested():
                            return
                        path = os.path.realpath(os.path.join(parent, name))
                        if (
                            not name.lower().endswith((".wad", ".pk3", ".ipk3"))
                            or path in seen
                        ):
                            continue
                        seen.add(path)
                        try:
                            found += int(
                                scan_game_file(
                                    path, repository, self.isInterruptionRequested
                                )
                            )
                        except (OSError, ValueError):
                            errors += 1
                            logging.getLogger(__name__).exception(
                                "Cannot scan %s", path
                            )
            self.completed.emit(len(directories), found, errors)
        except Exception as error:
            logging.getLogger(__name__).exception("Steam scan failed")
            self.failed.emit(str(error))
