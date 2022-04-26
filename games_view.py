import sys
import db
import os
import json
import platform
import logging

from PySide6 import QtCore, QtWidgets
from pathlib import Path
from mods_view import *

class GamesView(QtWidgets.QTableWidget):
    def __init__(self, runnerList):
        self.logger = logging.getLogger("Game List")
        match platform.system():
            case "Windows":
                self.settings = QtCore.QSettings("fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings("BoomerShooterLauncher", "Boomer Shooter Launcher")

        super().__init__()
        self.logger.debug("Building game list")
        self.runnerList = runnerList
        self.games = []
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
        self.settings.beginGroup("Games")
        self.setRowCount(len(self.settings.childGroups()))
        for i, base in enumerate(self.settings.childGroups(),start=0):
            self.settings.beginGroup(base)
            filesArray = []
            for j, game in enumerate(self.settings.childGroups(), start=0):
                self.settings.beginGroup(game)
                self.setItem(i,0,QtWidgets.QTableWidgetItem(self.settings.value("game")))
                self.setItem(i,1,QtWidgets.QTableWidgetItem(base))
                fileNameSplit = self.settings.value("path").split(os.sep)
                fileName = fileNameSplit[len(fileNameSplit) - 1]
                version = self.settings.value("version")
                filesArray.append(f"{fileName} - {version}")
                self.settings.endGroup()
            self.setItem(i, 2, QtWidgets.QTableWidgetItem(", ".join(filesArray)))
            self.settings.endGroup()
        self.settings.endGroup()
        try:
            self.bases = dbConnect.execute('SELECT * FROM Games GROUP BY base ORDER BY game').fetchall()
            allGames = dbConnect.execute('SELECT * FROM Games ORDER BY game').fetchall()
            for game in allGames:
                if os.path.exists(game[5]):
                    self.games.append(game)
                    self.row_data.append(game)
                else:
                    self.logger.debug(f"Removing {game}")
                    dbConnect.execute('DELETE FROM Games WHERE crc=?', (game[4],))
                    dbConnect.commit()
                    self.refresh()
                    break
            self.loadModpacks()
            self.sortItems(0, order=QtCore.Qt.AscendingOrder)
        except Exception as e:
            self.logger.exception(e)
        finally:
            dbConnect.close()

    def loadModpacks(self):
        self.logger.info("Refreshing modpacks")
        match platform.system():
            case "Windows":
                appData = os.getenv('APPDATA')
                path = Path(appData, "fullerSpectrum", "Boomer Shooter Launcher", "Modpacks")
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