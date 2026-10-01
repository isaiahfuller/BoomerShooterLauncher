"""The module for the modpack window"""
import os
import logging
from controllers.modpack_controller import ModpackController
from repositories.settings_repository import SettingsRepository
from PySide6 import QtCore, QtWidgets, QtGui


class ModsView(QtWidgets.QMainWindow):
    """Modpack editor window"""
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowModality(QtCore.Qt.ApplicationModal)

        self.logger = logging.getLogger("Modpack Editor")
        self.repository = getattr(parent, "repository", None) or SettingsRepository()

        self.controller = ModpackController(self.repository, self)
        self.controller.failed.connect(self._show_error)

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

    @property
    def mods(self):
        """Compatibility access to the controller-owned draft."""
        return self.controller.draft

    @mods.setter
    def mods(self, pack):
        self.controller.draft = pack

    def _show_error(self, message):
        error = QtWidgets.QErrorMessage(self)
        error.showMessage(message)

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
        """Submit a local file to the draft."""
        if self.controller.add_file(filePath):
            self.modList.addItem(self.mods.files[-1].name)


    def baseComboBuilder(self):
        """Render the controller's available families."""
        self.baseSelect.clear()
        self.baseSelect.addItems(self.controller.bases())
        self.controller.change(base=self.baseSelect.currentText())

    def baseChanged(self, text):
        self.controller.change(base=text)

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
        selected = self.controller.remove_file(self.modList.currentRow())
        if selected is not None:
            self.refreshFiles(selected)

    def addMod(self):
        """Open file chooser for mod file"""
        files = self.fileChooser.getOpenFileUrls()
        for file in files[0]:
            self.addFileToList(str(file.toLocalFile()))

    def changeModPosition(self, i):
        selected = self.controller.move_file(self.modList.currentRow(), i)
        if selected is not None:
            self.refreshFiles(selected)

    def moveUp(self):
        """Calls changeModPosition"""
        self.changeModPosition(-1)

    def moveDown(self):
        """Calls changeModPosition"""
        self.changeModPosition(1)

    def saveFile(self):
        if self.controller.save():
            self.close()

    def changeName(self, text):
        """Rename the draft; persistence waits until Save."""
        self.controller.change(name=text)

    def changeModName(self, text):
        """Change the selected file's name."""
        self.changeSelectedFile(name=text)

    def changeModSource(self, text):
        """Change the selected file's source."""
        self.changeSelectedFile(source=text)

    def changeSelectedFile(self, **changes):
        if self.selected is not None:
            self.controller.change_file(self.selected, **changes)

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
        """Render an existing draft supplied by the controller."""
        pack = self.controller.open(self.gameList.selected_record)
        self.nameEdit.setText(pack.name)
        with QtCore.QSignalBlocker(self.baseSelect):
            if self.baseSelect.findText(pack.base or "") < 0:
                self.baseSelect.addItem(pack.base or "")
            self.baseSelect.setCurrentText(pack.base or "")
        self.refreshFiles(0 if pack.files else -1)
        self.showWindow()

    def rmFile(self):
        if self.controller.remove(self.gameList.selected_record):
            self.gameList.refresh()

    def exportJson(self):
        """Choose a destination; the controller owns export."""
        chooser = QtWidgets.QFileDialog(self, "Save To...")
        chooser.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        chooser.setNameFilter("JSON (*.json)")
        chooser.setDefaultSuffix("json")
        if chooser.exec():
            self.controller.export_json(chooser.selectedFiles()[0])
