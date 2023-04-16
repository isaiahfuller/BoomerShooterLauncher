"""Generate GamesView"""
import os
import platform
import logging

from pathlib import Path
from PySide6 import QtCore, QtWidgets
from mods_view import ModsView

class GamesView(QtWidgets.QTableWidget):
    """Displays games in a table"""

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.status = parent.status
        self.logger = logging.getLogger("Game List")
        self.logger.debug("Building game list")
        match platform.system():
            case "Windows":
                self.settings = QtCore.QSettings("Isaiah Fuller", "Boomer Shooter Launcher")
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
        """Refresh list of games"""
        self.logger.info("Refreshing table")
        self.games.clear()
        self.rowData.clear()
        self.clearContents()
        self.settings.beginGroup("Games")
        self.setRowCount(len(self.settings.childGroups()))
        for i, base in enumerate(self.settings.childGroups(),start=0):
            self.settings.beginGroup(base)
            details = (self.settings.value("game"), base, self.settings.value("version"))
            self.rowData.append(details)
            filesArray = []
            for game in enumerate(self.settings.childGroups(), start=0):
                self.setItem(i,0,QtWidgets.QTableWidgetItem(self.settings.value("game")))
                self.settings.beginGroup(game[1])
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
        """Refresh list of modpacks"""
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
            details = (
                self.settings.value("base") +
                " (Modded)", pack, "modpack", 0, "modpack", files)
            items = self.findItems(self.settings.value("base"), QtCore.Qt.MatchExactly)
            if items:
                pos = items[len(items) - 1].row() + 1
                self.insertRow(pos)
                self.rowData.insert(pos, details)
                self.setItem(pos, 0, QtWidgets.QTableWidgetItem(details[0]))
                self.setItem(pos, 1, QtWidgets.QTableWidgetItem(details[1]))
                self.setItem(pos, 2, QtWidgets.QTableWidgetItem(", ".join(details[5])))
            self.settings.endGroup()
        self.settings.endGroup()

    def updateRow(self):
        """Stores information of the currently selected game"""
        if self.selectedItems():
            self.game = self.selectedItems()[1].text()
            self.settings.beginGroup("Games")
            bases = self.settings.childGroups()
            for i, val in enumerate(bases):
                category = self.settings.value(f"{val}/game")
                if self.selectedItems()[0].text().replace(" (Modded)", "") == category:
                    self.selectedRow = i
                    self.modpackSelected = True
                    self.files = self.selectedItems()[2].text().split(", ")
                    break
                if self.selectedItems()[0].text() == category:
                    self.selectedRow = i
                    self.modpackSelected = False
                    self.files.clear()
                    break
            self.settings.endGroup()

    def generateMenu(self, pos):
        """Open menu at current cursor position"""
        self.menu.exec_(self.mapToGlobal(pos))

    def eventFilter(self, qobject: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Create and populate context menu"""
        # pylint: disable=attribute-defined-outside-init
        if(event.type() == QtCore.QEvent.MouseButtonPress and
        event.buttons() == QtCore.Qt.RightButton and qobject is self.viewport()):
            item = self.itemAt(event.pos()).row()
            row = self.rowData[item]
            self.menu = QtWidgets.QMenu(self)
            modsView = ModsView(self)
            if row[2] == "modpack":
                self.menu.addAction("Edit modpack", modsView.openFile)
                self.menu.addAction("Remove modpack", modsView.rmFile)
            else:
                self.menu.addAction("Add modpack", modsView.showWindow)
        return super().eventFilter(qobject, event)
