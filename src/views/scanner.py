"""Choose game files and coordinate background directory scans."""

import logging
import os

from PySide6 import QtCore, QtGui, QtWidgets

from repositories.settings_repository import SettingsRepository
from services.game_files import scan_game_file

from services.scanner import DirectoryScanWorker


class GameScanner(QtWidgets.QFileDialog):
    """File chooser and owner of the manual scan workflow."""

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.refresh = None
        self.status = parent.status
        self.clearStatus = parent.clearStatus
        self.logger = logging.getLogger("Game Scanner")
        self.repository = SettingsRepository()
        self.setFileMode(QtWidgets.QFileDialog.Directory)

    def directoryCrawl(self, fileName, tableRefresh):
        """Scan a file or directory and refresh after background work ends."""
        self.refresh = tableRefresh
        self.logger.info("Scanning %s", fileName)
        if os.path.isdir(fileName):
            owner = self.parent()
            worker = DirectoryScanWorker(fileName, owner)
            owner.directoryScanners.append(worker)
            worker.progress.connect(self.status.showMessage)
            worker.finished.connect(tableRefresh)
            worker.finished.connect(self.clearStatus)
            worker.finished.connect(lambda: owner.directoryScanners.remove(worker))
            worker.finished.connect(worker.deleteLater)
            worker.start()
        else:
            self.individualFile(fileName)
        self.close()

    def individualFile(self, fileName):
        """Scan one selected file on the GUI thread."""
        fileName = os.path.realpath(fileName)
        self.status.showMessage(f"Scanning games... ({fileName})")
        try:
            return scan_game_file(fileName, self.repository)
        except (OSError, ValueError):
            self.logger.exception("Failed to scan file %s", fileName)
            return False

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.refresh is not None:
            self.refresh()
        self.deleteLater()
        return super().closeEvent(event)
