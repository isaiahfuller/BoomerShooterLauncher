"""Import mod packs"""
import sys
import logging
import webbrowser
import platform
import qtawesome as qta
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
        match platform.system():
            case "Windows":
                self.settings = QtCore.QSettings(
                    "fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings(
                    "boomershooterlauncher", "config")

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
        modInfo.addWidget(QtWidgets.QLabel(f"Base: {self.base}"), 0, 1)
        self.mods = {}
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
            self.mods[e["name"]] = { "source": e["source"], "found": False, "path": None}
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
        for i in range(len(self.mods)):
            text = self.modList.item(i,0).text()
            if text == fileName:
                if not self.mods[text]["found"]:
                    self.loadedCount+=1
                self.mods[text]["found"] = True
                self.mods[text]["path"] = file
                self.logger.debug(f"Setting {text} Path: {self.mods[text]['path']}")
                self.modList.setItem(i,2,QtWidgets.QTableWidgetItem(file))
                self.updateStatus()
                break

    def addModFile(self):
        """Adds mod to list"""
        chooser = QtWidgets.QFileDialog(self)
        chooser.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
        currentText = self.modList.item(self.modList.currentRow(),0).text()
        chooser.setNameFilter(f"{currentText} (*).{currentText.split('.')[-1]}")
        if chooser.exec():
            modFile = chooser.selectedFiles()[0]
            self.mods[currentText]["path"] = modFile
            if not self.mods[currentText]["found"]:
                self.loadedCount+=1
            self.mods[currentText]["found"] = True
            newPath = QtWidgets.QTableWidgetItem(modFile)
            self.modList.setItem(self.modList.currentRow(),2,newPath)
            self.updateStatus()

    def updateStatus(self):
        """Update mod counts in the status bar"""
        self.status.showMessage(f"{len(self.mods)} mods, {self.loadedCount} loaded")
        if self.loadedCount == len(self.mods):
            self.finishButton.setDisabled(False)

    def selectedModChanged(self, currentRow):
        """Updates vars on change"""
        currentItem = self.modList.item(currentRow,0).text()
        self.browseButton.setDisabled(False)
        if len(self.mods[currentItem]["source"]) > 0:
            self.downloadButton.setDisabled(False)
        else:
            self.downloadButton.setDisabled(True)

    def downloadMod(self):
        """Opens download page in default web browser"""
        currentItem = self.modList.item(self.modList.currentRow(),1).toolTip()
        webbrowser.open(currentItem)

    def saveModpack(self):
        """Saves modpack to registry and closes window"""
        self.logger.info(f"Saving modpack \"{self.name}\" for \"{self.base}\"")
        self.settings.beginGroup(f"Modpacks/{self.name}")
        self.settings.setValue("base", self.base)
        self.settings.beginWriteArray("files")
        names = list(self.mods.keys())
        for i in range(0,len(self.mods)):
            self.settings.setArrayIndex(i)
            self.settings.setValue("name", names[i])
            self.settings.setValue("path",self.mods[names[i]]["path"])
            self.settings.setValue("source",self.mods[names[i]]["source"])
        self.settings.endArray()
        self.settings.endGroup()
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
