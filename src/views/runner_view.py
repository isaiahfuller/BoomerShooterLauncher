"""Manage source ports"""
import logging
import webbrowser
from controllers.runner_controller import RunnerController
from repositories.settings_repository import SettingsRepository
from PySide6 import QtCore, QtWidgets, QtGui

class RunnerView(QtWidgets.QMainWindow):
    """Source port manager window and functions"""
    closed = QtCore.Signal()
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.logger = logging.getLogger("Runner Editor")
        self.logger.info("Opened")
        self.repository = getattr(parent, "repository", None) or SettingsRepository()
        self.controller = RunnerController(self.repository, self)
        self.controller.failed.connect(self.showError)

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
        """Render the controller's source-port choices."""
        self.controller.repository = self.repository
        self.runnerList.clear()
        self.game = game
        for runner, installed in self.controller.choices(game):
            self.addRunnerItem(runner, installed)
        self.addRunnerItem(None)
        self.updateText()

    def addRunnerItem(self, runner, installed=False):
        item = QtWidgets.QListWidgetItem(
            runner.name + (" [installed]" if installed else "") if runner else "Custom...")
        item.setData(QtCore.Qt.UserRole, runner)
        self.runnerList.addItem(item)

    def setRunner(self):
        """Render the selected runner's configuration."""
        item = self.runnerList.currentItem()
        record = item.data(QtCore.Qt.UserRole) if item else None
        self.controller.select(record, custom=item is not None and record is None)
        self.name = self.controller.name
        self.executable = self.controller.executable
        self.url = self.controller.url
        selected = self.name is not None
        self.descriptionLabel.setText(self.controller.description)
        self.programPath.setEnabled(selected)
        self.browseButton.setEnabled(selected)
        self.programPath.setPlaceholderText(
            "Not found on PATH — browse for a program" if selected
            else "Select a runner to find its executable")
        self.programPath.setText(self.controller.path)
        self.downloadButton.setEnabled(bool(self.url))
        self.removeButton.setEnabled(self.controller.installed)
        self.updateSaveButton()

    def updateSaveButton(self):
        """Submit path edits and render save availability."""
        self.controller.change_path(self.programPath.text())
        self.selectInstalledButton.setEnabled(self.controller.can_save)

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
        """Refresh configuration when the selection changes."""
        self.setRunner()

    def addToDb(self):
        """Save through the controller and refresh the displayed choices."""
        record = self.controller.save()
        if record is None:
            return
        self.builder(self.game)
        if not self.openedFromMenu:
            self.close()
        else:
            for row in range(self.runnerList.count()):
                item = self.runnerList.item(row)
                runner = item.data(QtCore.Qt.UserRole)
                if runner is not None and runner.name == record.name:
                    self.runnerList.setCurrentItem(item)
                    break

    def removeRunner(self):
        """Remove the selected record through the controller."""
        if self.controller.remove():
            self.builder(self.game)

    def showError(self, title, message):
        QtWidgets.QMessageBox.warning(self, title, message)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Refresh main window when closing"""
        self.runnerList.clear()
        self.openedFromMenu = False
        self.closed.emit()
        self.deleteLater()
        return super().closeEvent(event)
