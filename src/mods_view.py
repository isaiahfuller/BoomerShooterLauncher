"""The module for the modpack window"""
import os
import platform
import logging
import json
from PySide6 import QtCore, QtWidgets, QtGui


class ModsView(QtWidgets.QMainWindow):
    """Modpack editor window"""
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowModality(QtCore.Qt.ApplicationModal)

        self.logger = logging.getLogger("Modpack Editor")
        match platform.system():
            case "Windows":
                self.settings = QtCore.QSettings(
                    "fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings(
                    "boomershooterlauncher", "config")

        self.mods = {
            "name": "Mod name",
            "base": "",
            "files": []
        }

        self.setWindowTitle("Modpack Builder")

        self.gameList = self.parent()
        self.games = self.gameList.games

        mainLayout = QtWidgets.QVBoxLayout()
        header = QtWidgets.QHBoxLayout()
        modInfoBox = QtWidgets.QHBoxLayout()
        self.modList = QtWidgets.QListWidget()
        modInfoGrid = QtWidgets.QGridLayout()
        self.upButton = QtWidgets.QPushButton("▲", self)
        self.downButton = QtWidgets.QPushButton("▼", self)
        footer = QtWidgets.QHBoxLayout()

        moveButtons = QtWidgets.QVBoxLayout()
        moveButtons.setAlignment(QtCore.Qt.AlignTop)
        self.upButton.setMaximumWidth(35)
        self.downButton.setMaximumWidth(35)
        self.upButton.setDisabled(True)
        self.downButton.setDisabled(True)

        self.baseSelect = QtWidgets.QComboBox()
        self.nameEdit = QtWidgets.QLineEdit()

        baseLabel = QtWidgets.QLabel("Base game: ")
        nameLabel = QtWidgets.QLabel("Name: ")

        mainLayout.addLayout(header)

        mainLayout.addWidget(self.modList)
        mainLayout.addLayout(modInfoBox)

        moveButtons.addWidget(self.upButton)
        moveButtons.addWidget(self.downButton)

        modInfoBox.addLayout(moveButtons)
        modInfoBox.addLayout(modInfoGrid)

        header.addWidget(nameLabel)
        header.addWidget(self.nameEdit)
        header.addWidget(baseLabel)
        header.addWidget(self.baseSelect)
        header.setAlignment(QtCore.Qt.AlignJustify)
        self.nameEdit.setStyleSheet("QLineEdit{min-width: 130px;}")
        self.baseSelect.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents)

        scroll = QtWidgets.QScrollArea()
        scroll.setLayout(mainLayout)

        self.pathLabel = QtWidgets.QLabel("")
        self.pathLabel.setWordWrap(True)

        modInfoGrid.setAlignment(QtCore.Qt.AlignTop)
        modInfoGrid.addWidget(QtWidgets.QLabel("Name: "), 0, 0)
        modInfoGrid.addWidget(QtWidgets.QLabel("Source: "), 1, 0)
        modInfoGrid.addWidget(QtWidgets.QLabel("Path: "), 2, 0)

        self.modNameEdit = QtWidgets.QLineEdit()
        self.modSourceEdit = QtWidgets.QLineEdit()
        self.modSourceEdit.setStyleSheet("min-width: 150px;")
        modInfoGrid.addWidget(self.modNameEdit, 0, 1)
        modInfoGrid.addWidget(self.modSourceEdit, 1, 1)
        modInfoGrid.addWidget(self.pathLabel, 2, 1)

        exportPackButton = QtWidgets.QPushButton("Export", self)
        addFileButton = QtWidgets.QPushButton("Add", self)
        removeFileButton = QtWidgets.QPushButton("Remove", self)
        saveButton = QtWidgets.QPushButton("Save", self)
        footer.addWidget(exportPackButton)
        footer.addWidget(addFileButton)
        footer.addWidget(removeFileButton)
        footer.addWidget(saveButton)
        mainLayout.addLayout(footer)

        self.fileChooser = QtWidgets.QFileDialog(self)
        self.fileChooser.setFileMode(QtWidgets.QFileDialog.ExistingFiles)

        self.baseComboBuilder()

        self.setAcceptDrops(True)

        self.baseSelect.currentTextChanged.connect(self.baseChanged)
        self.modList.currentRowChanged.connect(self.selectedModChanged)

        addFileButton.clicked.connect(self.addMod)
        removeFileButton.clicked.connect(self.removeMod)

        self.upButton.clicked.connect(self.moveUp)
        self.downButton.clicked.connect(self.moveDown)
        saveButton.clicked.connect(self.saveFile)
        self.nameEdit.textEdited.connect(self.changeName)
        self.modNameEdit.textEdited.connect(self.changeModName)
        self.modSourceEdit.textEdited.connect(self.changeModSource)
        exportPackButton.clicked.connect(self.exportJson)

        self.selected = None

        self.setCentralWidget(scroll)

    def dragEnterEvent(self, event):
        """Filters things dragged into window"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Adds drag and dropped file to mod list"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for path in files:
            self.addFileToList(path)

    def addFileToList(self, filePath):
        """Adds mod to mod pack"""
        fileSplit = filePath.split("/")
        fileName = fileSplit[len(fileSplit) - 1]
        nameSplit = fileName.split(".")
        nameSplit[len(nameSplit) - 1] = ""
        modName = ".".join(nameSplit)
        modName = modName[0:len(modName) - 1]
        found = False
        for i in self.mods["files"]:
            if i["path"] == filePath:
                found = True
                break
        if not found:
            self.mods["files"].append(
                {"name": modName, "path": filePath, "source": ""})
            self.modNameEdit.setText(modName)
            self.pathLabel.setText(filePath)
            self.modList.addItem(fileName)

    def baseComboBuilder(self):
        """Generate base game combo box options"""
        self.baseSelect.clear()
        self.settings.beginGroup("Games")
        bases = []
        for game in self.settings.childGroups():
            if self.settings.value(f"{game}/game") not in bases:
                bases.append(self.settings.value(f"{game}/game"))
                self.baseSelect.addItem(self.settings.value(f"{game}/game"))
        self.settings.endGroup()
        bases.sort()
        self.mods["base"] = bases[0]

    def baseChanged(self, text):
        """Updates var on change"""
        self.mods["base"] = text

    def selectedModChanged(self, currentRow):
        """Updates vars on change"""
        self.modNameEdit.setText(self.mods["files"][currentRow]["name"])
        self.modSourceEdit.setText(self.mods["files"][currentRow]["source"])
        self.pathLabel.setText(self.mods["files"][currentRow]["path"])
        self.selected = currentRow
        row = self.modList.currentRow()
        if row == 0:
            self.upButton.setDisabled(True)
        else:
            self.upButton.setDisabled(False)
        if row == self.modList.count() - 1:
            self.downButton.setDisabled(True)
        else:
            self.downButton.setDisabled(False)

    def removeMod(self):
        """Removes mod from list"""
        row = self.modList.currentRow()
        self.modList.takeItem(row)
        self.mods["files"].pop(row)

    def addMod(self):
        """Open file chooser for mod file"""
        files = self.fileChooser.getOpenFileUrls()
        for file in files[0]:
            self.addFileToList(str(file.toLocalFile()))

    def changeModPosition(self, i):
        """Reorder mod entry"""
        row = self.modList.currentRow()
        tempRow = self.modList.takeItem(row+i)
        tempObj = self.mods["files"][row+i]
        self.modList.insertItem(row, tempRow)
        self.mods["files"][row+i] = self.mods["files"][row]
        self.mods["files"][row] = tempObj
        self.selected = self.modList.currentRow()

    def moveUp(self):
        """Calls changeModPosition"""
        self.changeModPosition(-1)

    def moveDown(self):
        """Calls changeModPosition"""
        self.changeModPosition(1)

    def saveFile(self):
        """Saves modpack to registry"""
        name = self.mods["name"]
        if name != "":
            self.settings.beginGroup(f"Modpacks/{name}")
            self.settings.setValue("base", self.mods["base"])
            self.settings.beginWriteArray("files")
            for i in range(0, len(self.mods["files"])):
                self.settings.setArrayIndex(i)
                self.settings.setValue("name", self.mods["files"][i]["name"])
                self.settings.setValue("path", self.mods["files"][i]["path"])
                self.settings.setValue(
                    "source", self.mods["files"][i]["source"])
            self.settings.endArray()
            self.settings.endGroup()
            self.close()

    def changeName(self, text):
        """Change name of mod file"""
        self.mods["name"] = text

    def changeModName(self, text):
        """Change name of mod pack"""
        self.mods["files"][self.selected]["name"] = text

    def changeModSource(self, text):
        """Change source url of mod pack"""
        self.mods["files"][self.selected]["source"] = text

    def showWindow(self):
        """Displays the window"""
        self.setFixedSize(500, 500)
        mainLocation = self.parent().parent().parent().parent().frameGeometry()
        x = mainLocation.x() + mainLocation.width() / 2 - self.width() / 2
        y = mainLocation.y() + mainLocation.height() / 2 - self.height() / 2
        self.move(x, y)
        self.show()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Refreshes game list while closing modpack menu"""
        self.gameList.refresh()
        self.deleteLater()
        return super().closeEvent(event)

    def openFile(self):
        """Loads mod pack from registry"""
        name = self.gameList.selectedItems()[1].text()
        self.settings.beginGroup(f"Modpacks/{name}")
        self.nameEdit.setText(name)
        self.baseSelect.setCurrentText(self.settings.value("base"))
        self.mods["name"] = name
        self.mods["base"] = self.settings.value("base")
        size = self.settings.beginReadArray("files")
        for i in range(0, size):
            self.settings.setArrayIndex(i)
            fileSplit = self.settings.value("path").split(os.sep)
            fileName = fileSplit[len(fileSplit) - 1]
            self.modList.addItem(fileName)
            self.mods["files"].append({
                    "name": self.settings.value("name"),
                    "path": self.settings.value("path"),
                    "source": self.settings.value("source")
                })
        self.settings.endArray()
        self.modNameEdit.setText(self.settings.value("files/1/name"))
        self.pathLabel.setText(self.settings.value("files/1/path"))
        self.modSourceEdit.setText(self.settings.value("files/1/source"))
        self.settings.endGroup()
        self.showWindow()

    def rmFile(self):
        """Removes mod pack"""
        name = self.gameList.selectedItems()[1].text()
        self.settings.remove("Modpacks/%s", name)
        self.logger.info("Removing %s", name)
        self.gameList.refresh()

    def exportJson(self):
        """Save current modpack to json file"""
        save_to = QtWidgets.QFileDialog().getSaveFileName(self, "Save To...",
            filter="JSON (*.json)")
        self.logger.info("Saving JSON to: %s", save_to[0])
        if not save_to[0]:
            return
        data = {
            "name": self.mods["name"],
            "base": self.mods["base"],
        }
        mods = self.mods["files"]
        for mod in mods:
            mod.pop("path", None)
        data["mods"] = mods
        with open(save_to[0], "w", encoding="utf-8") as outfile:
            outfile.write(json.dumps(data, indent=4))
