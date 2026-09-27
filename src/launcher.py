"""Launches game"""
import os
import logging
import platform
from pathlib import Path
from repositories.settings_repository import SettingsRepository
from PySide6 import QtCore, QtWidgets

class GameLauncher(QtCore.QProcess):
    """Launches game"""
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.logger = logging.getLogger("Launcher")
        self.repository = SettingsRepository()
        self.runner = None
        self.finished.connect(self.processFinished)

    def runGame(self, game, gamePath, runner, otherFiles):
        """Launches game"""
        # pylint: disable=anomalous-backslash-in-string
        self.runner = runner
        path = self.repository.runners()[runner]["path"]
        self.logger.debug(f"Game: {game} @ {gamePath}")
        self.logger.debug(f"Runner: {runner}")
        self.logger.debug(f"Path: {path}")
        self.logger.debug(f"Other files: {otherFiles}")
        runnerPath = Path(path)
        if not Path(path).is_file():
            raise FileNotFoundError("Executable missing")
        gameDir = str(gamePath).split(os.sep)
        gameDir.pop(len(gameDir) - 1)
        gameDir = Path("/".join(gameDir))
        spArray = [""]*3
        filteredTitle = self.parent().gameList.game
        filteredTitle = "".join(x for x in filteredTitle if x not in "\/:*?<>|\"")
        spArray = [str(runnerPath), "-iwad", gamePath]
        if len(otherFiles) > 0:
            spArray.append("-file")
        for i in otherFiles:
            spArray.append(i)
        match platform.system():
            case "Windows": runPath = Path(Path.home(), "AppData", "Roaming",
                "Boomer Shooter Launcher", "Saves", runner, filteredTitle)
            case "Linux": runPath = Path(Path.home(), ".local", "share",
                "Boomer Shooter Launcher", runner, filteredTitle)
        match runner:
            case "PrBoom+": savedir = "-save"
            case _: savedir = "-savedir"
        spArray.append(savedir)
        spArray.append(str(runPath))
        os.makedirs(runPath, exist_ok=True)
        os.chdir(runPath)
        self.logger.debug(f"Array: {spArray}")
        self.start(spArray[0], spArray[1:])

    def processFinished(self, exitCode=0):
        """Show error if there was one"""
        self.logger.info("Game closed")
        if exitCode != 0:
            errorWindow = QtWidgets.QErrorMessage(parent=self.parent())
            errorWindow.showMessage(f"{self.runner} exited with non-zero code {exitCode}.\
                                    Double check your runner and game version if modded.")
            self.logger.error(f"{self.runner} crashed. (Code {exitCode})")
