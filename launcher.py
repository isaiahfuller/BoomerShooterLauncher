import os
import logging
import sys 
import platform
from PySide6 import QtCore, QtWidgets
from pathlib import Path

class GameLauncher(QtCore.QProcess):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.logger = logging.getLogger("Game Scanner")
        match platform.system():    
            case "Windows":
                self.settings = QtCore.QSettings("fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings("Boomer Shooter Launcher", "config")
        self.finished.connect(self.processFinished)

    def runGame(self, game, game_path, runner, other_files):
        self.runner = runner
        self.logger.debug(f"Game: {game} @ {game_path}")
        self.logger.debug(f"Runner: {runner}")
        self.logger.debug(f"Other files: {other_files}")
        runner_path = Path(self.settings.value(f"Runners/{runner}/path"))
        game_dir = str(game_path).split(os.sep)
        game_dir.pop(len(game_dir) - 1)
        game_dir = Path("/".join(game_dir))
        spArray = [""]*3
        if game in ["Duke Nukem 3D", "Ion Fury"]:
            spArray = [str(runner_path), "-usecwd", "-nosetup",
                    "-gamegrp", game_path, "-game_dir", str(game_dir)]
            for i in other_files:
                spArray.append("-file")
                spArray.append(i)
        else:
            spArray = [str(runner_path), "-iwad", game_path]
            for i in other_files:
                spArray.append("-file")
                spArray.append(i)
        match platform.system():
            case "Windows": run_path = Path(Path.home(), "AppData", "Roaming", "Boomer Shooter Launcher", runner, self.parent().game_list.game)
            case "Linux": run_path = Path(Path.home(), ".local", "share", "Boomer Shooter Launcher", runner, self.parent().game_list.game)
        spArray.append("-savedir")
        spArray.append(str(run_path))
        os.makedirs(run_path, exist_ok=True)
        os.chdir(run_path)
        self.logger.debug(f"Array: {spArray}")
        self.start(spArray[0], spArray[1:])
    
    def processFinished(self, exitCode):
        self.logger.info("Game closed")
        if exitCode != 0:
            errorWindow = QtWidgets.QErrorMessage(parent=self.parent())
            errorWindow.showMessage(f"{self.runner} crashed (Code {exitCode}). Double check your runner and game version if modded.")
            self.logger.error(f"{self.runner} crashed. (Code {exitCode})")
