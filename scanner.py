import zlib
import db
import os
import data
import platform
import logging
from pathlib import Path
from PySide6 import QtWidgets


class GameScanner(QtWidgets.QFileDialog):
    def __init__(self):
        super().__init__()
        self.fileTypes = ("wad", "grp")
        self.setFileMode(QtWidgets.QFileDialog.Directory)
        self.setNameFilter("Game data directory")

    def crc(self, fileName, tableRefresh):
        self.directoryCrawl(fileName, tableRefresh)
    
    def directoryCrawl(self, fileName, tableRefresh):
        if os.path.isdir(fileName):
            for (dirpath, dirnames, filenames) in os.walk(fileName):
                for file in filenames:
                    if file.lower().endswith(self.fileTypes):
                        self.individualFile(os.path.join(dirpath, file), tableRefresh)
        else:
            self.individualFile(fileName, tableRefresh)


    def individualFile(self, fileName, tableRefresh):
        db.init()
        fileName = os.path.realpath(fileName)
        prev = 0
        fileNameSplit = fileName.split(os.sep)
        gameFileName = fileNameSplit[len(fileNameSplit) - 1]
        try:
            game = data.games[gameFileName.lower()]
            for eachLine in open(fileName, "rb"):
                prev = zlib.crc32(eachLine, prev)
            crc = "%X" % (prev & 0xFFFFFFFF)
            crc = crc.lower()
            found = False
            for i in game["releases"]:
                if i["crc"] == crc:
                    base = game["name"]
                    if "name" in i:
                        name = i["name"]
                    else:
                        name = game["name"]
                    gameInfo = (base, name, i["version"], game["year"], crc, fileName, game["runner"], game["game"])
                    db.addGame(gameInfo, tableRefresh, self)
                    found = True
                    break
            if not found:
                name = game["name"]
                gameInfo = (game["name"], f"{name} vUnk-{crc}", crc, game["year"], crc, fileName, game["runner"], game["game"])
                db.addGame(gameInfo, tableRefresh, self)
            logging.info(f"[Scanner] Added {gameInfo[0]} {gameInfo[1]} from {gameInfo[5]}")
        except Exception as e:
            logging.exception(e)
            logging.warning("[Scanner] Failed to scan file")