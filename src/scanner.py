"""Scans files for known games"""
import os
import logging
import threading
from threading import Thread
from repositories.settings_repository import SettingsRepository
from PySide6 import QtGui, QtWidgets
from services.game_files import scan_game_file

class GameScanner(QtWidgets.QFileDialog):
    """File chooser"""
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.refresh = None
        self.status = parent.status
        self.clearStatus = parent.clearStatus
        self.logger = logging.getLogger("Game Scanner")
        self.timer = None
        self.repository = SettingsRepository()
        self.fileTypes = ("wad", "pk3", "ipk3")
        # self.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
        self.setFileMode(QtWidgets.QFileDialog.Directory)
        # self.setNameFilter("Game files (*.wad, *.pk3, *.ipk3)")

    def directoryCrawl(self, fileName, tableRefresh):
        """Enumerate files and directories"""
        self.refresh = tableRefresh
        self.logger.info(f"Scanning directory {fileName}")
        if os.path.isdir(fileName):
            self.timer = threading.Timer(0.1, self.refresh)
            self.timer.start()
            t = Thread(target=self.directoryThread, args=(fileName,))
            t.daemon = True
            t.start()
        else:
            self.individualFile(fileName)
        self.close()

    def directoryThread(self, fileName):
        """Enumerate files and directories"""
        for (dirpath, dirnames, filenames) in os.walk(fileName): # pylint: disable=unused-variable
            for file in filenames:
                if file.lower().endswith(self.fileTypes):
                    self.timer.cancel()
                    self.logger.debug(f"Scanning {file}")
                    self.individualFile(os.path.join(dirpath, file))
                    self.timer = threading.Timer(0.1, self.refresh)
                    self.timer.start()
        self.clearStatus()
        self.refresh()

    def individualFile(self, fileName):
        """Scans file crc"""
        fileName = os.path.realpath(fileName)
        self.status.showMessage(f"Scanning games... ({fileName})")
        try:
            scan_game_file(fileName, self.repository)
        except Exception:
            self.logger.exception("Failed to scan file %s", fileName)

    def closeEvent(self, arg__1: QtGui.QCloseEvent) -> None:
        """Releases memory on close"""
        self.refresh()
        self.deleteLater()
        return super().closeEvent(arg__1)
