"""A game launcher for old FPS games"""
import sys
import os
import logging
import platform
import json
from PySide6 import QtCore, QtWidgets, QtGui
import qtawesome as qta
from discord import Discord
import data
from games_view import GamesView
from scanner import GameScanner
from runner_view import RunnerView
from mods_view import ModsView
from launcher import GameLauncher
from import_view import ModsImport
from theme import Theme
from first_run_view import FirstRun


class MainWindow(QtWidgets.QMainWindow):
    """Main launcher window"""

    def __init__(self):
        super().__init__()
        self.status = self.statusBar()
        self.logger = logging.getLogger("Main window")
        if "--debug" in sys.argv:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Debug mode")
        self.platform = platform.system()

        self.theme = Theme(app.setStyleSheet)

        match self.platform:
            case "Windows":
                self.settings = QtCore.QSettings(
                    "Isaiah Fuller", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings(
                    "boomershooterlauncher", "config")

        self.readSettings()
        self.discord = Discord()

        self.gameList = GamesView(self)
        self.process = None
        self.game = None
        self.discordTimer = QtCore.QTimer()
        self.discordDetails = ""
        self.discordState = ""
        self.currentRunners = []
        self.currentVersions = []
        self.runnerText = ""
        self.game_running = False
        self.originalPath = ""

        iconColor = "grey"
        plusIcon = qta.icon('fa5s.plus', color=iconColor)
        codeIcon = qta.icon('fa5s.code', color=iconColor)
        listIcon = qta.icon('fa5s.list-ol', color=iconColor)
        loadIcon = qta.icon('fa5s.file-download', color=iconColor)
        refreshIcon = qta.icon('fa5s.sync-alt', color=iconColor)

        self.gameList.setHorizontalHeaderLabels(["", "Name", "Files"])

        fileToolbar = self.addToolBar("Toolbar")
        self.addToolBarBreak()
        self.runnerToolbar = self.addToolBar("Launcher")
        fileToolbar.setMovable(False)

        fileToolbar.addAction(codeIcon, "&Manage Ports", self.showRunnerList)
        fileToolbar.addAction(plusIcon, "&Add Games", self.gameScanner)
        fileToolbar.addAction(listIcon, "&New Modpack", self.showModWindow)
        fileToolbar.addAction(loadIcon, "&Import Modpack", self.importModpack)

        fileToolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        if self.logger.level == logging.DEBUG:
            fileToolbar.addAction(refreshIcon, "&Refresh",
                                  self.gameList.refresh)

        self.runnerCombobox = QtWidgets.QComboBox()
        self.runnerCombobox.addItem("Select a game first")
        self.versionCombobox = QtWidgets.QComboBox()
        self.versionCombobox.addItem("Versions")
        self.launchButton = QtWidgets.QPushButton("Launch", self)
        self.runnerCombobox.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents)
        self.versionCombobox.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents)
        self.runnerCombobox.setEnabled(False)
        self.versionCombobox.setEnabled(False)

        self.runnerToolbar.addWidget(self.runnerCombobox)
        self.runnerToolbar.addWidget(self.versionCombobox)
        self.runnerToolbar.addWidget(self.launchButton)

        self.runnerToolbar.setStyleSheet("QToolBar{spacing: 5px;}")

        self.gameList.itemSelectionChanged.connect(self.getRunners)
        self.gameList.itemSelectionChanged.connect(self.getVersions)

        self.launchButton.clicked.connect(self.launchGame)
        self.gameList.cellActivated.connect(self.launchGame)

        self.discordTimer.start(30 * 1000)
        self.discordTimer.timeout.connect(self.updateStatus)
        self.clearStatus()
        self.updateStatus()

        self.setCentralWidget(self.gameList)
        self.setAcceptDrops(True)

    def writeSettings(self):
        """Write window geometry to registry"""
        self.settings.beginGroup("MainWindow")
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.endGroup()

    def readSettings(self):
        """Read window geometry from registry"""
        self.settings.beginGroup("MainWindow")
        geometry = self.settings.value("geometry", QtCore.QByteArray())
        firstRun = False
        if geometry.isEmpty():
            firstRun = True
            self.setGeometry(0, 0, 800, 600)
        else:
            self.restoreGeometry(geometry)
        if firstRun:
            self.logger.info("First run")
            FirstRun(self).showWindow()
        self.settings.endGroup()

    def gameScanner(self):
        """Scans files"""
        self.status.showMessage("Scanning games...")
        scanner = GameScanner(self)
        if scanner.exec():
            files = scanner.selectedFiles()
            scanner.directoryCrawl(files[0], self.gameList.refresh)
        self.clearStatus()
        self.gameList.refresh()
        scanner = None

    def getRunners(self):
        """Add all compatible source ports to combobox"""
        self.currentRunners.clear()
        self.runnerCombobox.clear()
        if self.gameList.selectedIndexes():
            game = self.gameList.selectedItems(
            )[0].text().replace(" (Modded)", "")

            self.game = game
            self.settings.beginGroup("Runners")
            res = self.settings.childGroups()
            self.settings.endGroup()
            lastRunner = self.settings.value(f"Games/{game}/Last Runner")
            if "(Modded)" in self.gameList.selectedItems()[0].text():
                lastRunner = self.settings.value(
                    f"Modpacks/{self.gameList.selectedItems()[1].text()}/Last Runner")
            if lastRunner:
                self.runnerCombobox.addItem(lastRunner)
            for x in res:
                if x == lastRunner:
                    continue
                for y in data.runners:  # pylint: disable=consider-using-dict-items
                    if game in data.runners[y]["games"] and x in y:
                        self.currentRunners.append(x)
                if x not in data.runners:
                    self.currentRunners.append(x)
            self.logger.debug(
                f"Compatible runners for \"{game}\": {self.currentRunners}")
            if len(self.currentRunners) == 0:
                self.runnerCombobox.adjustSize()
                self.runnerCombobox.setEnabled(False)
                self.runnerCombobox.addItem("Add source port")
            else:
                self.runnerCombobox.adjustSize()
                self.runnerCombobox.addItems(self.currentRunners)

                self.runnerCombobox.setEnabled(True)
        else:
            self.runnerCombobox.adjustSize()
            self.runnerCombobox.setEnabled(False)
            self.runnerCombobox.addItem("Select a game first")

    def getVersions(self):
        """Add all versions of the selected game to combobox"""
        self.currentVersions.clear()
        self.versionCombobox.clear()
        if self.gameList.selectedIndexes():
            self.settings.beginGroup("Games")
            bases = self.settings.childGroups()
            res = []
            if "(Modded)" in self.gameList.selectedItems()[0].text():
                game = self.gameList.selectedItems(
                )[0].text().replace(" (Modded)", "")
                self.settings.endGroup()
                lastVersion = self.settings.value(
                    f"Modpacks/{self.gameList.selectedItems()[1].text()}/Last Version")
                if lastVersion:
                    self.versionCombobox.addItem(lastVersion)
                self.settings.beginGroup("Games")
                for i in bases:
                    if self.settings.value(f"{i}/game") == game:
                        self.settings.beginGroup(i)
                        res = res + self.settings.childGroups()
                        self.settings.endGroup()
            else:
                game = self.gameList.selectedItems()[1].text()
                self.settings.beginGroup(game)
                lastVersion = self.settings.value("Last Version")
                if lastVersion:
                    self.versionCombobox.addItem(lastVersion)
                res = self.settings.childGroups()
                self.settings.endGroup()
            self.settings.endGroup()
            for x in res:
                self.currentVersions.append(x)
            for version in self.currentVersions:
                if version != lastVersion:
                    self.versionCombobox.addItem(version)
            self.versionCombobox.adjustSize()
            self.versionCombobox.setEnabled(True)
            self.logger.debug(f"\"{game}\" versions: {res}")
        else:
            self.versionCombobox.adjustSize()
            self.versionCombobox.setEnabled(False)
            self.versionCombobox.addItem("Versions")

    def launchGame(self):
        """Launch currently selected game with currently selected source port"""
        runnerList = RunnerView(self)
        version_text = self.versionCombobox.currentText()
        self.runnerText = self.runnerCombobox.currentText()
        self.process = GameLauncher(self)
        self.process.finished.connect(self.clearStatus)
        self.process.finished.connect(self.gameClosed)
        if "(Modded)" not in self.gameList.selectedItems()[0].text():
            game = self.gameList.selectedItems()[1].text()
            self.settings.setValue(
                f"Games/{game}/Last Runner", self.runnerText)
            self.settings.setValue(f"Games/{game}/Last Version", version_text)
            self.settings.beginGroup(f"Games/{game}/{version_text}")
        else:
            keys = self.settings.allKeys()
            for i in keys:
                if f"/{version_text}/crc" in i:
                    game = i.replace("/crc", "")
                    gameName = self.gameList.selectedItems()[1].text()
                    self.settings.setValue(
                        f"Modpacks/{gameName}/Last Runner", self.runnerText)
                    self.settings.setValue(
                        f"Modpacks/{gameName}/Last Version", version_text)
                    self.settings.beginGroup(game)
        try:
            game = self.settings.value("path")
            if len(self.currentRunners) == 0:
                runnerList.showWindow(self.game)
            else:
                self.originalPath = os.getcwd()
                if "(Modded)" in self.gameList.selectedItems()[0].text():
                    self.process.runGame(
                        self.game, game, self.runnerText, self.gameList.files)
                else:
                    self.process.runGame(self.game, game, self.runnerText, [])
                self.discordDetails = f"Playing {self.gameList.game} with {self.runnerText}"
                self.discordState = version_text
                self.game_running = True
                self.updateStatus()
                self.status.showMessage(
                    f"{self.discordDetails} ({version_text})")
        except Exception as e:  # pylint: disable=broad-except
            self.logger.exception(e)
            self.logger.error("Failed to launch game")
            errorWindow = QtWidgets.QErrorMessage(self)
            errorWindow.showMessage(f"Failed to launch game ({e})")
        finally:
            self.settings.endGroup()
            self.process = None
            runnerList = None

    def showModWindow(self):
        """Creates and displays the mod editor window"""
        mod_list = ModsView(self.gameList)
        mod_list.showWindow()

    def showRunnerList(self):
        """Creates and displays the runner window"""
        runnerList = RunnerView(self)
        runnerList.showWindowFromMenu()

    def importModpack(self):
        """Choose json file, open importer window"""
        self.status.showMessage("Selecting a modpack to import...")
        chooser = QtWidgets.QFileDialog(self)
        chooser.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
        chooser.setNameFilter("Modpack JSON (*.json)")
        if chooser.exec():
            pack_file = chooser.selectedFiles()[0]
            with open(pack_file, encoding="utf-8") as jsonFile:
                jsonData = json.load(jsonFile)
                importView = ModsImport(self, jsonData)
                importView.showWindow()
        self.status.showMessage("Idle...")

    def dragEnterEvent(self, event):
        """Filters things dragged into window"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Scans files and folders dropped onto the window as games"""
        scanner = GameScanner(self)
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for path in files:
            scanner.directoryCrawl(path, self.gameList.refresh)
            self.gameList.refresh()
        return super().dropEvent(event)

    def clearStatus(self):
        """Changes status after game closes"""
        self.discordState = "Idle..."
        self.discordDetails = "Looking at games"
        self.game_running = False
        self.status.showMessage("Idle...")
        self.updateStatus()

    def updateStatus(self):
        """Updates status"""
        self.discord.update(self.discordState, self.discordDetails)

    def gameClosed(self):
        """Changes working directory after game closes"""
        os.chdir(self.originalPath)

    def closeEvent(self, event: QtGui.QCloseEvent):
        """Saves settings before closing"""
        self.writeSettings()
        self.discord.clear()
        return super().closeEvent(event)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    logging.basicConfig()
    if "--debug" in sys.argv:
        logging.root.setLevel(logging.DEBUG)
    widget = MainWindow()
    widget.setWindowTitle("Boomer Shooter Launcher")
    widget.show()

    sys.exit(app.exec())
