import os
import platform
import logging
from PySide6 import QtCore, QtWidgets, QtGui


class ModsView(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowModality(QtCore.Qt.ApplicationModal)

        self.logger = logging.getLogger("Modpack Editor")
        match platform.system():
            case "Windows":
                self.settings = QtCore.QSettings(
                    "fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings("boomershooterlauncher", "config")

        self.mods = {
            "name": "Mod name",
            "base": "",
            "files": []
        }

        self.setWindowTitle("Modpack Builder")

        self.game_list = self.parent()
        self.games = self.game_list.games

        main_layout = QtWidgets.QVBoxLayout()
        header_line = QtWidgets.QHBoxLayout()
        centerHBox = QtWidgets.QHBoxLayout()
        self.center_left_list = QtWidgets.QListWidget()
        center_right_grid = QtWidgets.QGridLayout()
        centerVBox = QtWidgets.QVBoxLayout()
        self.up_button = QtWidgets.QPushButton("▲", self)
        self.down_button = QtWidgets.QPushButton("▼", self)
        footer_buttons = QtWidgets.QHBoxLayout()

        main_layout.addLayout(header_line)

        main_layout.addLayout(centerHBox)

        centerHBox.addWidget(self.center_left_list)
        centerHBox.addLayout(centerVBox)
        centerHBox.addLayout(center_right_grid)
        centerHBox.setContentsMargins(0, 0, 0, 0)
        centerHBox.setAlignment(QtCore.Qt.AlignCenter)

        centerVBox.setAlignment(QtCore.Qt.AlignVCenter)
        centerVBox.addWidget(self.up_button)
        centerVBox.addWidget(self.down_button)

        self.base_combobox = QtWidgets.QComboBox()
        self.name_edit = QtWidgets.QLineEdit()
        base_label = QtWidgets.QLabel("Base game: ")
        name_label = QtWidgets.QLabel("Name: ")

        header_line.addWidget(name_label)
        header_line.addWidget(self.name_edit)
        header_line.addWidget(base_label)
        header_line.addWidget(self.base_combobox)
        header_line.setAlignment(QtCore.Qt.AlignJustify)
        self.base_combobox.setStyleSheet("QComboBox{min-width: 200px;}")
        self.name_edit.setStyleSheet("QLineEdit{min-width: 150px;}")

        scroll = QtWidgets.QScrollArea()
        scroll.setLayout(main_layout)

        self.mod_path_label = QtWidgets.QLabel("")
        self.mod_path_label.setWordWrap(True)

        center_right_grid.setAlignment(QtCore.Qt.AlignTop)
        center_right_grid.addWidget(QtWidgets.QLabel("Name: "), 0, 0)
        center_right_grid.addWidget(QtWidgets.QLabel("Source: "), 1, 0)
        center_right_grid.addWidget(QtWidgets.QLabel("Path: "), 2, 0)

        self.mod_name_edit = QtWidgets.QLineEdit()
        self.mod_source_edit = QtWidgets.QLineEdit()
        self.mod_source_edit.setStyleSheet("min-width: 150px;")
        center_right_grid.addWidget(self.mod_name_edit, 0, 1)
        center_right_grid.addWidget(self.mod_source_edit, 1, 1)
        center_right_grid.addWidget(self.mod_path_label, 2, 1)

        add_file_button = QtWidgets.QPushButton("Add", self)
        remove_file_button = QtWidgets.QPushButton("Remove", self)
        save_button = QtWidgets.QPushButton("Save", self)
        footer_buttons.addWidget(add_file_button)
        footer_buttons.addWidget(remove_file_button)
        footer_buttons.addWidget(save_button)
        main_layout.addLayout(footer_buttons)

        self.file_chooser = QtWidgets.QFileDialog(self)
        self.file_chooser.setFileMode(QtWidgets.QFileDialog.ExistingFiles)

        self.baseComboBuilder()

        self.setAcceptDrops(True)

        self.base_combobox.currentTextChanged.connect(self.baseChanged)
        self.center_left_list.currentRowChanged.connect(
            self.selectedModChanged)

        add_file_button.clicked.connect(self.addMod)
        remove_file_button.clicked.connect(self.removeMod)

        self.up_button.clicked.connect(self.moveUp)
        self.down_button.clicked.connect(self.moveDown)
        save_button.clicked.connect(self.saveFile)
        self.name_edit.textEdited.connect(self.changeName)
        self.mod_name_edit.textEdited.connect(self.changeModName)
        self.mod_source_edit.textEdited.connect(self.changeModSource)

        self.setCentralWidget(scroll)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for path in files:
            self.addFileToList(path)

    def addFileToList(self, filePath):
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
            self.mod_name_edit.setText(modName)
            self.mod_path_label.setText(filePath)
            self.center_left_list.addItem(fileName)

    def baseComboBuilder(self):
        self.base_combobox.clear()
        self.settings.beginGroup("Games")
        bases = []
        for game in self.settings.childGroups():
            if self.settings.value(f"{game}/game") not in bases:
                bases.append(self.settings.value(f"{game}/game"))
                self.base_combobox.addItem(self.settings.value(f"{game}/game"))
        self.settings.endGroup()
        bases.sort()
        self.mods["base"] = bases[0]

    def baseChanged(self, text):
        self.mods["base"] = text

    def selectedModChanged(self, currentRow):
        self.mod_name_edit.setText(self.mods["files"][currentRow]["name"])
        self.mod_source_edit.setText(self.mods["files"][currentRow]["source"])
        self.mod_path_label.setText(self.mods["files"][currentRow]["path"])
        self.selected = currentRow
        row = self.center_left_list.currentRow()
        if row == 0: self.up_button.setDisabled(True)
        else: self.up_button.setDisabled(False)
        if row == self.center_left_list.count() - 1: self.down_button.setDisabled(True)
        else: self.down_button.setDisabled(False)

    def removeMod(self):
        row = self.center_left_list.currentRow()
        self.center_left_list.takeItem(row)
        self.mods["files"].pop(row)

    def addMod(self):
        files = self.file_chooser.getOpenFileUrls()
        for file in files[0]:
            self.addFileToList(str(file.toLocalFile()))

    def changeModPosition(self, i):
        row = self.center_left_list.currentRow()
        tempRow = self.center_left_list.takeItem(row+i)
        tempObj = self.mods["files"][row+i]
        self.center_left_list.insertItem(row, tempRow)
        self.mods["files"][row+i] = self.mods["files"][row]
        self.mods["files"][row] = tempObj
        self.selected = self.center_left_list.currentRow()

    def moveUp(self):
        self.changeModPosition(-1)

    def moveDown(self):
        self.changeModPosition(1)

    def saveFile(self):
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
        self.mods["name"] = text

    def changeModName(self, text):
        self.mods["files"][self.selected]["name"] = text

    def changeModSource(self, text):
        self.mods["files"][self.selected]["source"] = text

    def showWindow(self):
        self.setFixedSize(500, 500)
        mainLocation = self.parent().parent().parent().parent().frameGeometry()
        x = mainLocation.x() + mainLocation.width() / 2 - self.width() / 2
        y = mainLocation.y() + mainLocation.height() / 2 - self.height() / 2
        self.move(x, y)
        self.show()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.game_list.refresh()
        return super().closeEvent(event)

    def openFile(self):
        name = self.game_list.selectedItems()[1].text()
        self.settings.beginGroup(f"Modpacks/{name}")
        self.name_edit.setText(name)
        self.base_combobox.setCurrentText(self.settings.value("base"))
        self.mods["name"] = name
        self.mods["base"] = self.settings.value("base")
        size = self.settings.beginReadArray("files")
        for i in range(0, size):
            self.settings.setArrayIndex(i)
            fileSplit = self.settings.value("path").split(os.sep)
            fileName = fileSplit[len(fileSplit) - 1]
            self.center_left_list.addItem(fileName)
            self.mods["files"].append({"name": self.settings.value(
                "name"), "path": self.settings.value("path"), "source": self.settings.value("source")})
        self.settings.endArray()
        self.mod_name_edit.setText(self.settings.value("files/1/name"))
        self.mod_path_label.setText(self.settings.value("files/1/path"))
        self.mod_source_edit.setText(self.settings.value("files/1/source"))
        self.settings.endGroup()
        self.showWindow()

    def rmFile(self):
        name = self.game_list.selectedItems()[1].text()
        self.settings.remove(f"Modpacks/{name}")
        self.logger.info(f"Removing {name}")
        self.game_list.refresh()
