"""Manage source ports"""
import os
from pathlib import Path
import logging
import webbrowser
import shutil
from repositories.settings_repository import SettingsRepository
from PySide6 import QtCore, QtWidgets, QtGui
import data

class RunnerView(QtWidgets.QMainWindow):
    """Source port manager window and functions"""
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.logger = logging.getLogger("Runner Editor")
        self.logger.info("Opened")
        self.repository = SettingsRepository()

        self.boxLayout = QtWidgets.QVBoxLayout()
        self.openedFromMenu = False

        self.runnerList = QtWidgets.QListWidget()
        self.runnerList.itemSelectionChanged.connect(self.updateText)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setLayout(self.boxLayout)

        self.descriptionLabel = QtWidgets.QLabel()
        self.descriptionLabel.setWordWrap(True)

        self.name = None
        self.executable = None
        self.url = None
        self.game = None

        self.boxLayout.addWidget(self.runnerList)
        self.boxLayout.addWidget(self.descriptionLabel)

        self.boxLayout.addWidget(QtWidgets.QLabel("Program location:"))
        self.programPath = QtWidgets.QLineEdit()
        self.programPath.setPlaceholderText("Select a runner to find its executable")
        self.programPath.setEnabled(False)
        self.browseButton = QtWidgets.QPushButton("Browse…", self)
        self.browseButton.setEnabled(False)
        locationLayout = QtWidgets.QHBoxLayout()
        locationLayout.addWidget(self.programPath)
        locationLayout.addWidget(self.browseButton)
        self.boxLayout.addLayout(locationLayout)
        self.browseButton.clicked.connect(self.browseProgram)
        self.programPath.textChanged.connect(self.updateSaveButton)

        self.buttonBox = QtWidgets.QHBoxLayout()
        self.downloadButton = QtWidgets.QPushButton("Download", self)
        self.selectInstalledButton = QtWidgets.QPushButton("Save location", self)
        self.removeButton = QtWidgets.QPushButton("Remove", self)

        self.downloadButton.setEnabled(False)
        self.selectInstalledButton.setEnabled(False)
        self.removeButton.setEnabled(False)

        self.downloadButton.clicked.connect(self.getDownloadLink)
        self.selectInstalledButton.clicked.connect(self.addToDb)
        self.removeButton.clicked.connect(self.removeRunner)

        self.buttonBox.addWidget(self.downloadButton)
        self.buttonBox.addWidget(self.selectInstalledButton)
        self.buttonBox.addWidget(self.removeButton)

        self.boxLayout.addLayout(self.buttonBox)

        self.runnerDialog = QtWidgets.QFileDialog(parent=self)

        self.setCentralWidget(self.scroll)
        self.setWindowTitle("Source Ports")

    def showWindowFromMenu(self):
        """Displays the window, showing all source ports"""
        self.openedFromMenu = True
        self.showWindow("all")

    def showWindow(self, game):
        """Displays the window"""
        self.resize(400, 400)
        self.builder(game)
        mainLocation = self.parent().frameGeometry()
        x = mainLocation.x() + mainLocation.width() / 2 - self.width() / 2
        y = mainLocation.y() + mainLocation.height() / 2 - self.height() / 2
        self.move(x, y)
        self.show()

    def builder(self, game):
        """Builds list of source ports"""
        self.runnerList.clear()
        self.game = game
        if game == "all":
            allRunners = self.repository.runners()
            for i in allRunners:
                self.runnerList.addItem(f"{i} [installed]")
            for i in data.runners:
                if not self.runnerList.findItems(i, QtCore.Qt.MatchContains):
                    self.runnerList.addItem(i)
        else:
            for i in data.runners: # pylint: disable=consider-using-dict-items
                if game in data.runners[i]["games"]:
                    if not self.runnerList.findItems(i, QtCore.Qt.MatchExactly):
                        self.runnerList.addItem(i)
        self.runnerList.addItem("Custom...")
        self.updateText()

    def setRunner(self):
        """Change current runner to selected"""
        self.name = self.name.removesuffix(" [installed]")
        saved = self.repository.runners().get(self.name)
        self.url = None
        if self.name == "Custom...":
            self.executable = "*"
            self.descriptionLabel.setText("Add a runner that isn't listed.")
        elif self.name in data.runners:
            runner = data.runners[self.name]
            self.executable = runner["executable"]
            self.descriptionLabel.setText(runner["description"])
            self.url = runner["link"]
        else:
            self.executable = saved["executable"] if saved else self.name
            self.descriptionLabel.setText("Custom runner.")

        detected = shutil.which(self.executable) if self.executable != "*" else None
        self.programPath.setEnabled(True)
        self.browseButton.setEnabled(True)
        self.programPath.setPlaceholderText("Not found on PATH — browse for a program")
        # A saved override takes priority over automatic discovery.
        self.programPath.setText(saved["path"] if saved else (detected or ""))
        self.downloadButton.setEnabled(bool(self.url))
        self.removeButton.setEnabled(saved is not None)
        self.updateSaveButton()

    def updateSaveButton(self):
        """Enable saving once a runner and a location are supplied."""
        self.selectInstalledButton.setEnabled(
            self.name is not None and bool(self.programPath.text()))

    def browseProgram(self):
        """Choose an executable, including an override for an installed runner."""
        path, _ = self.runnerDialog.getOpenFileName(
            self, "Choose runner program", self.programPath.text())
        if path:
            self.programPath.setText(path)

    def getDownloadLink(self):
        """Opens download page in default web browser"""
        webbrowser.open(self.url)

    def updateText(self):
        """Change name to currently selected source port"""
        item = self.runnerList.currentItem()
        if item is None:
            self.name = None
            self.programPath.clear()
            self.programPath.setEnabled(False)
            self.browseButton.setEnabled(False)
            self.downloadButton.setEnabled(False)
            self.removeButton.setEnabled(False)
            return
        self.name = item.text()
        self.setRunner()

    def addToDb(self):
        """Save the detected or user-selected executable location."""
        if self.name is None or not self.programPath.text():
            return
        path = Path(self.programPath.text()).expanduser()
        if not path.is_file() or not os.access(path, os.X_OK):
            QtWidgets.QMessageBox.warning(
                self, "Invalid program", "Choose an existing executable file.")
            return
        name = path.name if self.name == "Custom..." else self.name
        try:
            self.repository.save_runner(name, str(path.absolute()), self.executable)
        except OSError as error:
            self.logger.exception("Failed to save runner %s", name)
            QtWidgets.QMessageBox.warning(self, "Unable to save runner", str(error))
            return
        self.builder(self.game)
        if not self.openedFromMenu:
            self.close()
        else:
            matches = self.runnerList.findItems(f"{name} [installed]", QtCore.Qt.MatchExactly)
            if matches:
                self.runnerList.setCurrentItem(matches[0])

    def removeRunner(self):
        """Removes source port from registry and combo box"""
        self.repository.remove_runner(self.name)
        self.builder(self.game)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Refresh main window when closing"""
        self.runnerList.clear()
        self.openedFromMenu = False
        self.parent().getRunners()
        self.deleteLater()
        return super().closeEvent(event)
