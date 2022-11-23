"""Launches game"""
import os
import logging
import platform
from pathlib import Path
from PySide6 import QtCore, QtWidgets

class GameLauncher(QtCore.QProcess):
    """Launches game"""
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.logger = logging.getLogger("Game Scanner")
        match platform.system():
            case "Windows":
                self.settings = QtCore.QSettings("fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings("boomershooterlauncher", "config")
        self.runner = None
        self.finished.connect(self.processFinished)

    def runGame(self, game, gamePath, runner, otherFiles):
        """Launches game"""
        # pylint: disable=anomalous-backslash-in-string
        self.runner = runner
        self.settings.beginGroup("Runners")
        path = self.settings.value(f"{runner}/path")
        self.logger.debug(f"Game: {game} @ {gamePath}")
        self.logger.debug(f"Runner: {runner}")
        self.logger.debug(f"Path: {path}")
        self.logger.debug(f"Other files: {otherFiles}")
        runnerPath = Path(self.settings.value(f"{runner}/path"))
        gameDir = str(gamePath).split(os.sep)
        gameDir.pop(len(gameDir) - 1)
        gameDir = Path("/".join(gameDir))
        spArray = [""]*3
        filteredTitle = self.parent().gameList.game
        filteredTitle = "".join(x for x in filteredTitle if x not in "\/:*?<>|\"")
        self.settings.endGroup()
        if game in ["Duke Nukem 3D", "Ion Fury"]:
            spArray = [str(runnerPath), "-usecwd", "-nosetup",
                    "-gamegrp", gamePath, "-game_dir", str(gameDir)]
            for i in otherFiles:
                spArray.append("-file")
                spArray.append(i)
        else:
            spArray = [str(runnerPath), "-iwad", gamePath]
            for i in otherFiles:
                spArray.append("-file")
                spArray.append(i)
        match platform.system():
            case "Windows": runPath = Path(Path.home(), "AppData", "Roaming",
                "Boomer Shooter Launcher", "Saves", runner, filteredTitle)
            case "Linux": runPath = Path(Path.home(), ".local", "share",
                "Boomer Shooter Launcher", runner, filteredTitle)
        spArray.append("-savedir")
        spArray.append(str(runPath))
        os.makedirs(runPath, exist_ok=True)
        os.chdir(runPath)
        self.logger.debug(f"Array: {spArray}")
        self.start(spArray[0], spArray[1:])

    def processFinished(self, exitCode):
        """Show error if there was one"""
        self.logger.info("Game closed")
        if exitCode != 0:
            errorWindow = QtWidgets.QErrorMessage(parent=self.parent())
            errorWindow.showMessage(f"{self.runner} exited with non-zero code {exitCode}.\
                                    Double check your runner and game version if modded.")
            self.logger.error(f"{self.runner} crashed. (Code {exitCode})")
