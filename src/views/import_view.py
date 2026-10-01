"""Import mod packs"""
import sys
from controllers.modpack_controller import ModpackController
import logging
import webbrowser
import qtawesome as qta
from repositories.settings_repository import SettingsRepository
from PySide6 import QtCore, QtWidgets, QtGui

class ModsImport(QtWidgets.QMainWindow):
    """Modpack importer"""
    saved = QtCore.Signal()
    def __init__(self, parent, data):
        super().__init__(parent=parent)
        parent = self.parent()
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.status = self.statusBar()
        self.logger = logging.getLogger("Modpack Importer")
        if "--debug" in sys.argv:
            self.logger.setLevel(logging.DEBUG)
        self.logger.info(f"{data}")
        self.repository = getattr(parent, "repository", None) or SettingsRepository()
        self.controller = ModpackController(self.repository, self, draft=data)
        pack = self.controller.draft
        self.controller.failed.connect(self.status.showMessage)

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
        self.name = pack.name
        self.base = pack.base
        mods = pack.files
        self.modList.setRowCount(len(mods))
        self.loadedCount = 0
        modInfo.setAlignment(QtCore.Qt.AlignTop)
        modInfo.addWidget(QtWidgets.QLabel(f"Name: {self.name}"), 0, 0)
        modInfo.addWidget(QtWidgets.QLabel(f"Base Game: {self.base}"), 1, 0)
        # Ordered records are supplied by the controller.
        count = 0
        greenCheck = qta.icon("fa5s.check", color="green")
        redXmark = qta.icon("fa5s.times", color="red")
        for e in mods:
            self.modList.setItem(count,0,QtWidgets.QTableWidgetItem(e.name))
            if e.source:
                source = QtWidgets.QTableWidgetItem(greenCheck,"")
            else:
                source = QtWidgets.QTableWidgetItem(redXmark,"")
            source.setToolTip(e.source or "")
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

    @property
    def mods(self):
        return self.controller.draft.files

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
        row = self.controller.resolve_dropped(file)
        if row is not None:
            self.modList.setItem(row, 2, QtWidgets.QTableWidgetItem(file))
            self.updateStatus()

    def setModPath(self, row, path):
        """Resolve a file by row identity, preserving duplicate names and order."""
        if self.controller.change_file(row, path=path):
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
        self.loadedCount = self.controller.loaded_count
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
        if self.controller.save(require_resolved=True):
            self.saved.emit()
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
