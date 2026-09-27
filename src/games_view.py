"""Generate GamesView"""
import os
import logging

from pathlib import Path
from repositories.settings_repository import SettingsRepository
from PySide6 import QtCore, QtWidgets
from mods_view import ModsView

class GamesView(QtWidgets.QTableWidget):
    """Displays games in a table"""

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.status = parent.status
        self.logger = logging.getLogger("Game List")
        self.logger.debug("Building game list")
        self.repository = SettingsRepository()

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
        games = self.repository.games()
        self.setRowCount(len(games))
        for i, (base, game) in enumerate(games.items()):
            self.rowData.append((game["game"], base, game["version"]))
            files = []
            self.setItem(i, 0, QtWidgets.QTableWidgetItem(game["game"]))
            self.setItem(i, 1, QtWidgets.QTableWidgetItem(base))
            for release in game["releases"].values():
                file_name = release["path"].split(os.sep)[-1]
                files.append(f"{file_name} - {release['version']}")
            self.setItem(i, 2, QtWidgets.QTableWidgetItem(", ".join(files)))
        self.loadModpacks()

    def loadModpacks(self):
        """Refresh list of modpacks"""
        self.logger.info("Refreshing modpacks")
        for name, pack in self.repository.modpacks().items():
            files = [str(Path(file["path"]).resolve()) for file in pack["files"]]
            details = (pack["base"] + " (Modded)", name, "modpack", 0, "modpack", files)
            items = self.findItems(pack["base"], QtCore.Qt.MatchExactly)
            if items:
                pos = items[len(items) - 1].row() + 1
                self.insertRow(pos)
                self.rowData.insert(pos, details)
                self.setItem(pos, 0, QtWidgets.QTableWidgetItem(details[0]))
                self.setItem(pos, 1, QtWidgets.QTableWidgetItem(details[1]))
                self.setItem(pos, 2, QtWidgets.QTableWidgetItem(", ".join(details[5])))

    def updateRow(self):
        """Stores information of the currently selected game"""
        if self.selectedItems():
            self.game = self.selectedItems()[1].text()
            for i, game in enumerate(self.repository.games().values()):
                category = game["game"]
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
