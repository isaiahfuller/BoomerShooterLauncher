import json
import os
from PySide6 import QtCore, QtWidgets, QtGui


class ModsView(QtWidgets.QMainWindow):
    def __init__(self, games):
        super().__init__()

        self.mods = {
            "name": "Mod name",
            "base": "",
            "files": []
        }

        self.setWindowTitle("Modpack Builder")

        self.game_list = games
        self.games = games.games
        self.bases = []

        main_layout = QtWidgets.QVBoxLayout()
        header_line = QtWidgets.QHBoxLayout()
        centerHBox = QtWidgets.QHBoxLayout()
        self.center_left_list = QtWidgets.QListWidget()
        center_right_grid = QtWidgets.QGridLayout()
        centerVBox = QtWidgets.QVBoxLayout()
        up_button = QtWidgets.QPushButton("▲", self)
        down_button = QtWidgets.QPushButton("▼", self)
        footer_buttons = QtWidgets.QHBoxLayout()

        main_layout.addLayout(header_line)

        main_layout.addLayout(centerHBox)

        centerHBox.addWidget(self.center_left_list)
        centerHBox.addLayout(centerVBox)
        centerHBox.addLayout(center_right_grid)
        centerHBox.setContentsMargins(0, 0, 0, 0)
        centerHBox.setAlignment(QtCore.Qt.AlignCenter)

        centerVBox.setAlignment(QtCore.Qt.AlignVCenter)
        centerVBox.addWidget(up_button)
        centerVBox.addWidget(down_button)

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
        self.center_left_list.currentRowChanged.connect(self.selectedModChanged)

        add_file_button.clicked.connect(self.addMod)
        remove_file_button.clicked.connect(self.removeMod)

        up_button.clicked.connect(self.moveUp)
        down_button.clicked.connect(self.moveDown)
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
        print(self.mods)

    def addFileToList(self, filePath):
        fileSplit = filePath.split("/")
        fileName = fileSplit[len(fileSplit) - 1]
        nameSplit = fileName.split(".")
        nameSplit[len(nameSplit) - 1] = ""
        modName = ".".join(nameSplit)
        modName = modName[0:len(modName) - 1]
        print(f"{filePath}\n{fileName}\n{modName}")
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
        for game in self.games:
            print(game[7])
            if game[7] not in self.bases:
                self.base_combobox.addItem(game[7])
                self.bases.append(game[7])
        self.mods["base"] = self.bases[0]

    def baseChanged(self, text):
        self.mods["base"] = text

    def selectedModChanged(self, currentRow):
        self.mod_name_edit.setText(self.mods["files"][currentRow]["name"])
        self.mod_source_edit.setText(self.mods["files"][currentRow]["source"])
        self.mod_path_label.setText(self.mods["files"][currentRow]["path"])
        self.selected = currentRow

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
        if row + i > self.center_left_list.count() - 1: print("no")
        elif row + i < 0: print("on")
        else:
            tempRow = self.center_left_list.takeItem(row+i)
            tempObj = self.mods["files"][row+i]
            self.center_left_list.insertItem(row, tempRow)
            self.mods["files"][row+i] = self.mods["files"][row]
            self.mods["files"][row] = tempObj
            self.selected = self.center_left_list.currentRow()
            print(self.mods)

    def moveUp(self):
        self.changeModPosition(-1)

    def moveDown(self):
        self.changeModPosition(1)

    def saveFile(self):
        name = self.mods["name"]
        if name != "":
            appData = os.getenv('APPDATA')
            path = os.path.join(appData, "Boomer Shooter Launcher", "Modpacks")
            os.makedirs(path, exist_ok=True)
            json_string = json.dumps(self.mods, indent=4)
            try:
                with open(os.path.join(path, f"{name}.json"), "w+") as outfile:
                    outfile.write(json_string)
            finally:
                outfile.close()
                self.game_list.refresh()
                self.close()

    def changeName(self, text):
        self.mods["name"] = text

    def changeModName(self, text):
        self.mods["files"][self.selected]["name"] = text

    def changeModSource(self, text):
        self.mods["files"][self.selected]["source"] = text

    def showWindow(self):
        self.setFixedSize(500, 500)
        self.show()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.game_list.refresh()
        return super().closeEvent(event)

    def openFile(self):
        name = self.game_list.selectedItems()[1].text()
        path = os.path.join(os.getenv('APPDATA'), "Boomer Shooter Launcher", "Modpacks", f"{name}.json")
        file = open(path)
        json_data = json.load(file)
        print(json_data)
        self.name_edit.setText(json_data["name"])
        self.base_combobox.setCurrentText(json_data["base"])
        for file in json_data["files"]:
            fileSplit = os.path.abspath(file["path"]).split(os.sep)
            fileName = fileSplit[len(fileSplit) - 1]
            self.center_left_list.addItem(fileName)
        self.mod_name_edit.setText(json_data["files"][0]["name"])
        self.mod_path_label.setText(json_data["files"][0]["path"])
        self.mod_source_edit.setText(json_data["files"][0]["source"])
        self.mods = json_data
        self.showWindow()