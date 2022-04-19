import sys
import db
import os
import json
import platform
import logging

from PySide6 import QtCore, QtWidgets
from collections import defaultdict
from pathlib import Path
from mods_view import *

class GamesView(QtWidgets.QTableWidget):
    def __init__(self, runnerList):
        self.logger = logging.getLogger("Game List")
        if "--debug" in sys.argv:
            self.logger.setLevel(logging.DEBUG)
        match platform.system():
            case "Windows":
                self.settings = QtCore.QSettings("fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings("BoomerShooterLauncher", "Boomer Shooter Launcher")

        super().__init__()
        self.runnerList = runnerList
        self.games = []
        self.bases = []
        self.modpacks = []
        self.files = []
        self.row_data = []
        self.game = ""
        self.selected_row = 0
        self.modpack_selected = False
        
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.setColumnCount(3)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.generateMenu)
        self.viewport().installEventFilter(self)

        self.refresh()
        self.itemSelectionChanged.connect(self.updateRow)

    def refresh(self):
        self.logger.info("Refreshing table")
        self.games.clear()
        self.row_data.clear()
        self.clearContents()
        dbConnect = db.connect()
        # print(self.settings.value("Bases/The Plutonia Experiment"))
        self.settings.beginGroup("Games")
        settingsGroups = self.settings.childGroups()
        for group in settingsGroups:
            self.settings.beginGroup(group)
            # print(group)
            # print(self.settings.childGroups())
            # print(self.settings.value("base"))
            # print(self.settings.value("name"))
            # print(self.settings.value("version"))
            # print(self.settings.value("year"))
            # print(self.settings.value("crc"))
            # print(self.settings.value("path"))
            # print(self.settings.value("runner"))
            # print(self.settings.value("game"))
            self.settings.endGroup()
        self.settings.endGroup()
        try:
            self.setRowCount(dbConnect.execute('SELECT count(DISTINCT base) from Games').fetchone()[0])
            self.bases = dbConnect.execute('SELECT * FROM Games GROUP BY base ORDER BY game').fetchall()
            allGames = dbConnect.execute('SELECT * FROM Games ORDER BY game').fetchall()
            count = 0
            filesArray = defaultdict(list)
            for game in allGames:
                if os.path.exists(game[5]):
                    self.games.append(game)
                    self.row_data.append(game)
                    if game in self.bases:
                        self.setItem(count, 0, QtWidgets.QTableWidgetItem(game[7]))
                        self.setItem(count, 1, QtWidgets.QTableWidgetItem(game[0]))
                        count = count + 1
                    fileNameSplit = game[5].split(os.sep)
                    fileName = fileNameSplit[len(fileNameSplit) - 1]
                    filesArray[game[0]].append(f"{fileName} - {game[2]}")
                else:
                    self.logger.debug(f"Removing {game}")
                    dbConnect.execute('DELETE FROM Games WHERE crc=?', (game[4],))
                    dbConnect.commit()
                    self.refresh()
                    break
            for i in range(len(self.bases)):
                self.setItem(i, 2, QtWidgets.QTableWidgetItem(", ".join(filesArray[self.bases[i][0]])))
            self.loadModpacks()
        except Exception as e:
            self.logger.exception(e)
        finally:
            dbConnect.close()

    def loadModpacks(self):
        self.logger.info("Refreshing modpacks")
        match platform.system():
            case "Windows":
                appData = os.getenv('APPDATA')
                path = Path(appData, "Boomer Shooter Launcher", "Modpacks")
            case "Linux":
                path = Path(Path.home(), ".config", "BoomerShooterLauncher", "Modpacks")
        os.makedirs(path, exist_ok=True)
        modpacks = [os.path.join(path, f) for f in os.listdir(path)]
        for pack in modpacks:
            with open(pack) as json_file:
                data = json.load(json_file)
                self.modpacks.append(data)
                list = (data["base"] + " (Modded)", data["name"], "modpack", 0, "modpack", [])
                for file in data["files"]:
                    list[5].append(os.path.realpath(file["path"]))
                items = self.findItems(data["base"], QtCore.Qt.MatchExactly)
                if items:
                    pos = items[len(items) - 1].row() + 1
                    self.insertRow(pos)
                    self.row_data.insert(pos, list)
                    self.setItem(pos, 0, QtWidgets.QTableWidgetItem(list[0]))
                    self.setItem(pos, 1, QtWidgets.QTableWidgetItem(list[1]))
                    self.setItem(pos, 2, QtWidgets.QTableWidgetItem(", ".join(list[5])))

    def updateRow(self):
        if self.selectedItems():
            self.game = self.selectedItems()[1].text()
            for i in range(len(self.bases)):
                if self.selectedItems()[0].text().replace(" (Modded)", "") == self.bases[i][7]:
                    self.selected_row = i
                    self.modpack_selected = True
                    self.files = self.selectedItems()[2].text().split(", ")
                    break
                elif self.selectedItems()[0].text() == self.bases[i][7]:
                    self.selected_row = i
                    self.modpack_selected = False
                    self.files.clear()
                    break

    def generateMenu(self, pos):
        self.menu.exec_(self.mapToGlobal(pos))

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if(event.type() == QtCore.QEvent.MouseButtonPress and event.buttons() == QtCore.Qt.RightButton and object is self.viewport()):
            item = self.itemAt(event.pos()).row()
            row = self.row_data[item]
            self.menu = QtWidgets.QMenu(self)
            if row[2] == "modpack":
                self.mods_view = ModsView(self)
                edit = self.menu.addAction("Edit modpack", self.mods_view.openFile)
                delete = self.menu.addAction("Remove modpack", self.mods_view.rmFile)
        return super().eventFilter(object, event)