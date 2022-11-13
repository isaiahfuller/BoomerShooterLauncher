"""Manage source ports"""
import os
from pathlib import Path
import logging
import webbrowser
import platform
import subprocess
from PySide6 import QtCore, QtWidgets, QtGui
import data

class RunnerView(QtWidgets.QMainWindow):
    """Source port manager window and functions"""
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.logger = logging.getLogger("Modpack Editor")

        match platform.system():
            case "Windows":
                self.settings = QtCore.QSettings("fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings("boomershooterlauncher", "config")

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

        self.buttonBox = QtWidgets.QHBoxLayout()
        self.downloadButton = QtWidgets.QPushButton("Download", self)
        self.selectInstalledButton = QtWidgets.QPushButton("Select", self)
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
            self.settings.beginGroup("Runners")
            allRunners = self.settings.childGroups()
            self.settings.endGroup()
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

    def setRunner(self):
        """Change current runner to selected"""
        installed = "[installed]" in self.name
        self.name = self.name.replace(" [installed]", "")
        if self.name == "Custom...":
            self.executable = "*"
            self.descriptionLabel.setText("Add a runner that isn't listed.")
            self.selectInstalledButton.setEnabled(True)
            self.downloadButton.setEnabled(False)
            self.removeButton.setEnabled(False)
        elif self.name not in data.runners:
            self.executable = self.name
            self.descriptionLabel.setText("Custom runner.")
            self.selectInstalledButton.setEnabled(False)
            self.removeButton.setEnabled(True)
            self.downloadButton.setEnabled(False)
        else:
            for i in data.runners: # pylint: disable=consider-using-dict-items
                if i == self.name:
                    self.executable = data.runners[i]["executable"]
                    self.descriptionLabel.setText(data.runners[i]["description"])
                    self.url = data.runners[i]["link"]
                    self.downloadButton.setEnabled(True)
                    if installed: 
                        self.selectInstalledButton.setEnabled(False)
                        self.removeButton.setEnabled(True)
                    else: 
                        self.selectInstalledButton.setEnabled(True)
                        self.removeButton.setEnabled(False)
                    break

    def getDownloadLink(self):
        """Opens download page in default web browser"""
        webbrowser.open(self.url)

    def updateText(self):
        """Change name to currently selected source port"""
        self.name = self.runnerList.currentItem().text()
        self.setRunner()

    def addToDb(self):
        """Adds source port to registry"""
        self.runnerDialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        selectedText = self.runnerList.selectedItems()[0].text()
        match platform.system():
            case "Windows":
                files = self.runnerDialog.getOpenFileUrl()
                filePath = files[0].toLocalFile()
            case "Linux":
                exe = self.executable
                if exe == "*":
                    files = self.runnerDialog.getOpenFileUrl()
                    filePath = files[0].toLocalFile()
                else:
                    file = subprocess.run(["which", exe], stdout=subprocess.PIPE, check=True)
                    filePath = Path(file.stdout.decode("utf-8"))
        try:
            if filePath != "":
                if self.name == "Custom...":
                    self.settings.beginGroup(f"Runners/{Path(filePath).name}")
                else: self.settings.beginGroup(f"Runners/{selectedText}")
                self.settings.setValue("path", str(filePath).strip())
                self.settings.setValue("executable", self.executable)
                self.settings.endGroup()
        except Exception as e: # pylint: disable=broad-except
            logging.exception(e)
            logging.warning(f"[Runner List] Failed to add {selectedText} to db")
        finally:
            if len(os.fspath(filePath)) > 0:
                self.builder(self.game)
                self.selectInstalledButton.setEnabled(False)
                if not self.openedFromMenu:
                    self.close()

    def removeRunner(self):
        """Removes source port from registry and combo box"""
        self.settings.remove(f"Runners/{self.name}")
        self.builder(self.game)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Refresh main window when closing"""
        self.runnerList.clear()
        self.openedFromMenu = False
        self.parent().getRunners()
        return super().closeEvent(event)
