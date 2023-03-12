"""Import mod packs"""
import sys
import logging
import json
import webbrowser
import platform
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
            self.logger.debug("Debug mode")
        self.logger.info(f"{data}")
        match platform.system():
            case "Windows":
                self.settings = QtCore.QSettings(
                    "fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings(
                    "boomershooterlauncher", "config")

        mainLayout = QtWidgets.QVBoxLayout()
        self.modList = QtWidgets.QListWidget()
        scroll = QtWidgets.QScrollArea()
        modInfo = QtWidgets.QGridLayout()

        scroll.setWidgetResizable(True)
        scroll.setLayout(mainLayout)

        mainLayout.addLayout(modInfo)
        mainLayout.addWidget(self.modList)
        self.name = data["name"]
        self.base = data["base"]
        mods = data["mods"]
        self.loadedCount = 0
        modInfo.setAlignment(QtCore.Qt.AlignTop)
        modInfo.addWidget(QtWidgets.QLabel(f"Name: {self.name}"), 0, 0)
        modInfo.addWidget(QtWidgets.QLabel(f"Base: {self.base}"), 0, 1)
        self.mods = {}
        for e in mods:
            self.modList.addItem(e["name"])
            self.mods[e["name"]] = { "source": e["source"], "found": False, "path": None}
        print(json.dumps(data, indent=4))

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
        self.modList.currentRowChanged.connect(self.selectedModChanged)

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
        """placeholder"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for path in files:
            self.addDroppedModFile(path)
        return super().dropEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Close"""
        self.deleteLater()
        return super().closeEvent(event)

    def addDroppedModFile(self, file):
        """Add mod file to list"""
        fileName = file.split("/")[-1]
        for i in range(self.modList.count()):
            text = self.modList.item(i).text()
            if text == fileName:
                if not self.mods[text]["found"]:
                    self.loadedCount+=1
                self.mods[text]["found"] = True
                self.mods[text]["path"] = file
                print(self.mods[text])
                self.updateStatus()
                break

    def addModFile(self):
        """Adds mod to list"""
        chooser = QtWidgets.QFileDialog(self)
        chooser.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
        currentItem = self.modList.currentItem()
        currentText = currentItem.text()
        if chooser.exec():
            modFile = chooser.selectedFiles()[0]
            self.mods[currentText]["path"] = modFile
            if not self.mods[currentText]["found"]:
                self.loadedCount+=1
            self.mods[currentText]["found"] = True
            print(self.mods[currentText])
            self.updateStatus()

    def updateStatus(self):
        """Update mod counts in the status bar"""
        self.status.showMessage(f"{len(self.mods)} mods, {self.loadedCount} loaded")
        if self.loadedCount == len(self.mods):
            self.finishButton.setDisabled(False)

    def selectedModChanged(self, currentRow):
        """Updates vars on change"""
        print(currentRow)
        currentItem = self.modList.item(currentRow).text()
        self.browseButton.setDisabled(False)
        if len(self.mods[currentItem]["source"]) > 0:
            self.downloadButton.setDisabled(False)
        else:
            self.downloadButton.setDisabled(True)

    def downloadMod(self):
        """Opens download page in default web browser"""
        currentItem = self.modList.currentItem().text()
        url = self.mods[currentItem]["source"]
        webbrowser.open(url)

    def saveModpack(self):
        """Saves modpack to registry and closes window"""
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
        self.close()

    def showWindow(self):
        """Open window and set size/location"""
        self.resize(400,400)
        mainLocation = self.parent().frameGeometry()
        x = mainLocation.x() + mainLocation.width() / 2 - self.width() / 2
        y = mainLocation.y() + mainLocation.height() / 2 - self.height() / 2
        self.move(x, y)
        self.setWindowTitle("Import modpack...")
        self.show()
