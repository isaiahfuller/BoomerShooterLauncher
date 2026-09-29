"""The module for the modpack window"""
import os
import logging
import json
from dataclasses import replace
from models.records import ModFile, Modpack
from repositories.settings_repository import SettingsRepository
from PySide6 import QtCore, QtWidgets, QtGui


class ModsView(QtWidgets.QMainWindow):
    """Modpack editor window"""
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowModality(QtCore.Qt.ApplicationModal)

        self.logger = logging.getLogger("Modpack Editor")
        self.repository = SettingsRepository()

        self.mods = Modpack("Mod name", "", ())
        self.original_name = None

        self.setWindowTitle("Modpack Builder")

        self.gameList = self.parent()

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
        # modInfoGrid.addWidget(QtWidgets.QLabel("Name: "), 0, 0)
        modInfoGrid.addWidget(QtWidgets.QLabel("Source: "), 0, 0)
        modInfoGrid.addWidget(QtWidgets.QLabel("Path: "), 1, 0)

        # self.modNameEdit = QtWidgets.QLineEdit()
        self.modSourceEdit = QtWidgets.QLineEdit()
        self.modSourceEdit.setStyleSheet("min-width: 150px;")
        # modInfoGrid.addWidget(self.modNameEdit, 0, 1)
        modInfoGrid.addWidget(self.modSourceEdit, 0, 1)
        modInfoGrid.addWidget(self.pathLabel, 1, 1)

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
        # self.modNameEdit.textEdited.connect(self.changeModName)
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
        if any(file.path == filePath for file in self.mods.files):
            return
        file = ModFile(os.path.basename(filePath), filePath, "")
        self.mods = replace(self.mods, files=self.mods.files + (file,))
        self.modList.addItem(file.name)


    def baseComboBuilder(self):
        """Generate base game combo box options"""
        self.baseSelect.clear()
        bases = sorted({game.family for game in self.repository.library().games
                        if game.family})
        self.baseSelect.addItems(bases)
        self.mods = replace(self.mods, base=self.baseSelect.currentText())

    def baseChanged(self, text):
        """Update the draft base family."""
        self.mods = replace(self.mods, base=text)

    def selectedModChanged(self, currentRow):
        """Display the selected file, including an empty selection."""
        self.selected = currentRow if 0 <= currentRow < len(self.mods.files) else None
        file = self.mods.files[self.selected] if self.selected is not None else None
        self.modSourceEdit.setText((file.source or "") if file else "")
        self.pathLabel.setText((file.path or "") if file else "")
        self.modSourceEdit.setEnabled(file is not None)
        self.upButton.setEnabled(file is not None and currentRow > 0)
        self.downButton.setEnabled(file is not None and currentRow < len(self.mods.files) - 1)

    def refreshFiles(self, selected=-1):
        """Render the draft after an order or membership change."""
        with QtCore.QSignalBlocker(self.modList):
            self.modList.clear()
            for file in self.mods.files:
                self.modList.addItem(file.name or os.path.basename(file.path or ""))
            self.modList.setCurrentRow(selected)
        self.selectedModChanged(selected)

    def removeMod(self):
        """Remove only a selected file."""
        row = self.modList.currentRow()
        if not 0 <= row < len(self.mods.files):
            return
        self.mods = replace(self.mods, files=self.mods.files[:row] + self.mods.files[row + 1:])
        self.refreshFiles(min(row, len(self.mods.files) - 1))

    def addMod(self):
        """Open file chooser for mod file"""
        files = self.fileChooser.getOpenFileUrls()
        for file in files[0]:
            self.addFileToList(str(file.toLocalFile()))

    def changeModPosition(self, i):
        """Reorder mod entry"""
        row = self.modList.currentRow()
        target = row + i
        if not (0 <= row < len(self.mods.files) and 0 <= target < len(self.mods.files)):
            return
        files = list(self.mods.files)
        files[row], files[target] = files[target], files[row]
        self.mods = replace(self.mods, files=tuple(files))
        self.refreshFiles(target)

    def moveUp(self):
        """Calls changeModPosition"""
        self.changeModPosition(-1)

    def moveDown(self):
        """Calls changeModPosition"""
        self.changeModPosition(1)

    def saveFile(self):
        """Saves modpack to registry"""
        if self.mods.name:
            self.repository.save_modpack_record(self.mods)
            if self.original_name and self.original_name != self.mods.name:
                runner, version = self.repository.last_selection(self.original_name, modpack=True)
                self.repository.save_selection(self.mods.name, runner, version, modpack=True)
                self.repository.remove_modpack(self.original_name)
            self.close()

    def changeName(self, text):
        """Rename the draft; persistence waits until Save."""
        self.mods = replace(self.mods, name=text)

    def changeModName(self, text):
        """Change the selected file's name."""
        self.changeSelectedFile(name=text)

    def changeModSource(self, text):
        """Change the selected file's source."""
        self.changeSelectedFile(source=text)

    def changeSelectedFile(self, **changes):
        if self.selected is None:
            return
        files = list(self.mods.files)
        files[self.selected] = replace(files[self.selected], **changes)
        self.mods = replace(self.mods, files=tuple(files))

    def showWindow(self):
        """Displays the window"""
        self.setFixedSize(500, 500)
        mainLocation = self.parent().parent().frameGeometry()
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
        name = self.gameList.selected_record.name
        pack = next(pack for pack in self.repository.library().modpacks if pack.name == name)
        self.original_name = name
        self.nameEdit.setText(name)
        if self.baseSelect.findText(pack.base or "") < 0:
            self.baseSelect.addItem(pack.base or "")
        self.baseSelect.setCurrentText(pack.base or "")
        self.mods = pack
        self.refreshFiles(0 if pack.files else -1)
        self.showWindow()

    def rmFile(self):
        """Removes mod pack"""
        name = self.gameList.selected_record.name
        self.repository.remove_modpack(name)
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
            "name": self.mods.name,
            "base": self.mods.base,
            "mods": [{"name": file.name, "source": file.source} for file in self.mods.files],
        }
        with open(save_to[0], "w", encoding="utf-8") as outfile:
            outfile.write(json.dumps(data, indent=4))
