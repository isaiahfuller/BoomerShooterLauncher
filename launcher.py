import os
import logging
import sys 
import platform
from PySide6 import QtCore

class GameLauncher(QtCore.QProcess):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("Game Scanner")
        match platform.system():    
            case "Windows":
                self.settings = QtCore.QSettings("fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings("BoomerShooterLauncher", "Boomer Shooter Launcher")

    def runGame(self, game, game_path, runner, other_files):
        self.logger.debug(f"Game: {game} @ {game_path}")
        self.logger.debug(f"Runner: {runner}")
        self.logger.debug(f"Other files: {other_files}")
        runner_path = str(runner[2]).split("/")
        runner_path.pop(len(runner_path) - 1)
        runner_path = os.path.realpath("/".join(runner_path))
        game_dir = str(game_path).split("\\")
        game_dir.pop(len(game_dir) - 1)
        game_dir = os.path.realpath("/".join(game_dir))
        spArray = [""]*3
        if runner[1] == "doom":
            spArray = [str(runner[2]), "-iwad", game_path]
            for i in other_files:
                spArray.append("-file")
                spArray.append(i)
            if runner[0] == "Chocolate Doom":
                mouse = open('./MOUSE.CFG')
                spArray.append("-config")
                spArray.append(os.path.realpath(mouse.name))
        if runner[1] == "build":
            if game in ["Duke Nukem 3D", "Ion Fury"]:
                spArray = [str(runner[2]), "-usecwd", "-nosetup",
                        "-gamegrp", game_path, "-game_dir", game_dir]
                for i in other_files:
                    spArray.append("-file")
                    spArray.append(i)
        return (spArray, runner_path)
