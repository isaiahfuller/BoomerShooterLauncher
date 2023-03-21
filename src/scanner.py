"""Scans files for known games"""
import os
import zlib
import logging
import platform
import threading
from threading import Thread
from PySide6 import QtGui, QtWidgets, QtCore
import data

class GameScanner(QtWidgets.QFileDialog):
    """File chooser"""
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.refresh = None
        self.status = parent.status
        self.clearStatus = parent.clearStatus
        self.logger = logging.getLogger("Game Scanner")
        self.timer = None
        match platform.system():
            case "Windows":
                self.settings = QtCore.QSettings("Isaiah Fuller", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings("boomershooterlauncher", "config")
        self.fileTypes = ("wad", "pk3", "ipk3")
        self.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
        self.setNameFilter("Game files (*.wad, *.pk3, *.ipk3)")

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
        prev = 0
        fileNameSplit = fileName.split(os.sep)
        gameFileName = fileNameSplit[len(fileNameSplit) - 1]
        if gameFileName.lower() in data.games: # pylint: disable=too-many-nested-blocks
            self.logger.debug(f"Filename {gameFileName} found")
            try:
                game = data.games[gameFileName.lower()]
                for eachLine in open(fileName, "rb"):
                    prev = zlib.crc32(eachLine, prev)
                crc = "%X" % (prev & 0xFFFFFFFF) # pylint: disable=consider-using-f-string
                crc = crc.lower()
                found = False
                if crc not in data.gameBlacklist:
                    for i in game["releases"]:
                        if i["crc"] == crc:
                            base = game["name"]
                            if "name" in i:
                                name = i["name"]
                            else:
                                name = game["name"]
                            gameInfo = (base, name, i["version"], game["year"],
                                        crc, fileName, game["runner"], game["game"])
                            found = True
                            self.logger.debug(f"{gameFileName} crc {crc} matches")
                            break
                    if not found:
                        name = game["name"]
                        base = name
                        gameInfo = (name, f"{name} vUnk-{crc}", crc, game["year"],
                                    crc, fileName, game["runner"], game["game"])
                        self.logger.debug(f"{gameFileName} crc {crc} doesn't match")
                    self.settings.beginGroup(f"Games/{gameInfo[0]}")
                    self.settings.beginGroup(gameInfo[1])
                    self.settings.setValue("version", gameInfo[2])
                    self.settings.setValue("crc", gameInfo[4])
                    self.settings.setValue("path", gameInfo[5])
                    self.settings.endGroup()
                    self.settings.setValue("year", gameInfo[3])
                    self.settings.setValue("game", gameInfo[7])
                    self.settings.endGroup()
                    self.logger.info(f"Added {gameInfo[0]}: {gameInfo[1]} from {gameInfo[5]}")
                else:
                    self.logger.info(f"Blacklisted crc {crc} found")
            except Exception as e: # pylint: disable=broad-except
                self.logger.exception(e)
                self.logger.warning(f"Failed to scan file {fileName}")

    def closeEvent(self, arg__1: QtGui.QCloseEvent) -> None:
        """Releases memory on close"""
        self.refresh()
        self.deleteLater()
        return super().closeEvent(arg__1)
