"""Import mod packs"""
import sys
from dataclasses import replace
from models.records import ModFile, Modpack
import logging
import webbrowser
import qtawesome as qta
from repositories.settings_repository import SettingsRepository
from PySide6 import QtCore, QtWidgets, QtGui

class ModsImport(QtWidgets.QMainWindow):
    """Modpack importer"""
    def __init__(self, parent, data):
        super().__init__(parent=parent)
        parent = self.parent()
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.status = self.statusBar()
        self.logger = logging.getLogger("Modpack Importer")
        if "--debug" in sys.argv:
            self.logger.setLevel(logging.DEBUG)
        self.logger.info(f"{data}")
        self.repository = SettingsRepository()

        mainLayout = QtWidgets.QVBoxLayout()
        self.modList = QtWidgets.QTableWidget()
        scroll = QtWidgets.QScrollArea()
        modInfo = QtWidgets.QGridLayout()

        scroll.setWidgetResizable(True)
        scroll.setLayout(mainLayout)
        self.modList.setColumnCount(3)
        self.modList.setHorizontalHeaderLabels(["Name", "Source", "Path"])
        self.modList.setAlternatingRowColors(True)
        self.modList.setWordWrap(True)
        self.modList.verticalHeader().setVisible(False)
        self.modList.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.modList.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.modList.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        header = self.modList.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

        mainLayout.addLayout(modInfo)
        mainLayout.addWidget(self.modList)
        self.name = data["name"]
        self.base = data["base"]
        mods = data["mods"]
        self.modList.setRowCount(len(mods))
        self.loadedCount = 0
        modInfo.setAlignment(QtCore.Qt.AlignTop)
        modInfo.addWidget(QtWidgets.QLabel(f"Name: {self.name}"), 0, 0)
        modInfo.addWidget(QtWidgets.QLabel(f"Base Game: {self.base}"), 1, 0)
        self.mods = tuple(ModFile(mod["name"], None, mod["source"]) for mod in mods)
        count = 0
        greenCheck = qta.icon("fa5s.check", color="green")
        redXmark = qta.icon("fa5s.times", color="red")
        for e in mods:
            self.modList.setItem(count,0,QtWidgets.QTableWidgetItem(e["name"]))
            if len(e["source"]) > 0:
                source = QtWidgets.QTableWidgetItem(greenCheck,"")
            else:
                source = QtWidgets.QTableWidgetItem(redXmark,"")
            source.setToolTip(e["source"])
            self.modList.setItem(count,1,source)
            count+=1
        count = None
        self.downloadButton = QtWidgets.QPushButton("Download", self)
        self.browseButton = QtWidgets.QPushButton("Browse", self)
        self.finishButton = QtWidgets.QPushButton("Finish", self)
        self.downloadButton.setDisabled(True)
        self.browseButton.setDisabled(True)
        self.finishButton.setDisabled(True)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.downloadButton)
        buttons.addWidget(self.browseButton)
        buttons.addWidget(self.finishButton)
        mainLayout.addLayout(buttons)

        self.browseButton.clicked.connect(self.addModFile)
        self.downloadButton.clicked.connect(self.downloadMod)
        self.finishButton.clicked.connect(self.saveModpack)
        self.modList.currentCellChanged.connect(self.selectedModChanged)

        self.setCentralWidget(scroll)
        self.setAcceptDrops(True)
        self.updateStatus()

    def dragEnterEvent(self, event):
        """Filters things dragged into window"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Matches selected files by filename"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for path in files:
            self.logger.info(f"Adding dropped file: {path}")
            self.addDroppedModFile(path)
        return super().dropEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Close"""
        self.deleteLater()
        return super().closeEvent(event)

    def addDroppedModFile(self, file):
        """Add mod file to list"""
        fileName = file.split("/")[-1]
        for row, mod in enumerate(self.mods):
            if mod.name == fileName and mod.path is None:
                self.setModPath(row, file)
                break

    def setModPath(self, row, path):
        """Resolve a file by row identity, preserving duplicate names and order."""
        mods = list(self.mods)
        mods[row] = replace(mods[row], path=path)
        self.mods = tuple(mods)
        self.modList.setItem(row, 2, QtWidgets.QTableWidgetItem(path))
        self.updateStatus()

    def addModFile(self):
        """Choose a local file for the selected entry."""
        row = self.modList.currentRow()
        if not 0 <= row < len(self.mods):
            return
        chooser = QtWidgets.QFileDialog(self)
        chooser.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        name = self.mods[row].name or ""
        chooser.setNameFilter(f"{name} (*).{name.split('.')[-1]}")
        if chooser.exec():
            self.setModPath(row, chooser.selectedFiles()[0])

    def updateStatus(self):
        """Update mod counts in the status bar"""
        self.loadedCount = sum(mod.path is not None for mod in self.mods)
        self.status.showMessage(f"{len(self.mods)} mods, {self.loadedCount} loaded")
        self.finishButton.setEnabled(self.loadedCount == len(self.mods))

    def selectedModChanged(self, currentRow):
        """Updates vars on change"""
        valid = 0 <= currentRow < len(self.mods)
        self.browseButton.setEnabled(valid)
        self.downloadButton.setEnabled(valid and bool(self.mods[currentRow].source))

    def downloadMod(self):
        """Open the selected record's source."""
        row = self.modList.currentRow()
        if 0 <= row < len(self.mods) and self.mods[row].source:
            webbrowser.open(self.mods[row].source)

    def saveModpack(self):
        """Saves modpack to registry and closes window"""
        self.logger.info(f"Saving modpack \"{self.name}\" for \"{self.base}\"")
        if any(mod.path is None for mod in self.mods):
            return
        self.repository.save_modpack_record(Modpack(self.name, self.base, self.mods))
        self.parent().gameList.refresh()
        self.close()

    def showWindow(self):
        """Open window and set size/location"""
        self.resize(700,500)
        mainLocation = self.parent().frameGeometry()
        x = mainLocation.x() + mainLocation.width() / 2 - self.width() / 2
        y = mainLocation.y() + mainLocation.height() / 2 - self.height() / 2
        self.move(x, y)
        self.setWindowTitle("Import modpack...")
        self.show()
