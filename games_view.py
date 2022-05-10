import os
import platform
import logging

from PySide6 import QtCore, QtWidgets
from pathlib import Path
from mods_view import *

class GamesView(QtWidgets.QTableWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.logger = logging.getLogger("Game List")
        self.logger.debug("Building game list")
        match platform.system():
            case "Windows":
                self.settings = QtCore.QSettings("fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings("boomershooterlauncher", "config")

        self.games = []
        self.files = []
        self.rowData = []
        self.game = ""
        self.selectedRow = 0
        self.modpackSelected = False
        
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
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
        self.rowData.clear()
        self.clearContents()
        self.settings.beginGroup("Games")
        self.setRowCount(len(self.settings.childGroups()))
        for i, base in enumerate(self.settings.childGroups(),start=0):
            self.settings.beginGroup(base)
            list = (self.settings.value("game"), base, self.settings.value("version"))
            self.rowData.append(list)
            filesArray = []
            for j, game in enumerate(self.settings.childGroups(), start=0):
                self.setItem(i,0,QtWidgets.QTableWidgetItem(self.settings.value("game")))
                self.settings.beginGroup(game)
                self.setItem(i,1,QtWidgets.QTableWidgetItem(base))
                fileNameSplit = self.settings.value("path").split(os.sep)
                fileName = fileNameSplit[len(fileNameSplit) - 1]
                version = self.settings.value("version")
                filesArray.append(f"{fileName} - {version}")
                self.settings.endGroup()
            self.setItem(i, 2, QtWidgets.QTableWidgetItem(", ".join(filesArray)))
            self.settings.endGroup()
        self.settings.endGroup()
        self.loadModpacks()

    def loadModpacks(self):
        self.logger.info("Refreshing modpacks")
        self.settings.beginGroup("Modpacks")
        for pack in self.settings.childGroups():
            self.settings.beginGroup(pack)
            files = []
            size = self.settings.beginReadArray("files")
            for i in range(0, size):
                self.settings.setArrayIndex(i)
                files.append(str(Path(self.settings.value("path")).resolve()))
            self.settings.endArray()
            list = (self.settings.value("base") + " (Modded)", pack, "modpack", 0, "modpack", files)
            items = self.findItems(self.settings.value("base"), QtCore.Qt.MatchExactly)
            if items:
                pos = items[len(items) - 1].row() + 1
                self.insertRow(pos)
                self.rowData.insert(pos, list)
                self.setItem(pos, 0, QtWidgets.QTableWidgetItem(list[0]))
                self.setItem(pos, 1, QtWidgets.QTableWidgetItem(list[1]))
                self.setItem(pos, 2, QtWidgets.QTableWidgetItem(", ".join(list[5])))
            self.settings.endGroup()
        self.settings.endGroup()

    def updateRow(self):
        if self.selectedItems():
            self.game = self.selectedItems()[1].text()
            self.settings.beginGroup("Games")
            bases = self.settings.childGroups()
            for i in range(len(bases)):
                category = self.settings.value(f"{bases[i]}/game")
                if self.selectedItems()[0].text().replace(" (Modded)", "") == category:
                    self.selectedRow = i
                    self.modpackSelected = True
                    self.files = self.selectedItems()[2].text().split(", ")
                    break
                elif self.selectedItems()[0].text() == category:
                    self.selectedRow = i
                    self.modpackSelected = False
                    self.files.clear()
                    break
            self.settings.endGroup()

    def generateMenu(self, pos):
        self.menu.exec_(self.mapToGlobal(pos))

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if(event.type() == QtCore.QEvent.MouseButtonPress and event.buttons() == QtCore.Qt.RightButton and object is self.viewport()):
            item = self.itemAt(event.pos()).row()
            row = self.rowData[item]
            self.menu = QtWidgets.QMenu(self)
            self.modsView = ModsView(self)
            if row[2] == "modpack":
                edit = self.menu.addAction("Edit modpack", self.modsView.openFile)
                delete = self.menu.addAction("Remove modpack", self.modsView.rmFile)
            else:
                add = self.menu.addAction("Add modpack", self.modsView.showWindow)
        return super().eventFilter(object, event)