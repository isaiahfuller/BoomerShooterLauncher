"""A game launcher for old FPS games"""
import sys
import os
import logging
import platform
import json
from models.records import Modpack
from repositories.settings_repository import SettingsRepository
from PySide6 import QtCore, QtWidgets, QtGui
import qtawesome as qta
from discord import Discord
from games_view import GamesView
from scanner import GameScanner
from steam_scanner import SteamScanner
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

        self.repository = SettingsRepository()

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
        self.steamScanAction = fileToolbar.addAction(
            "Find Steam Games", self.scanSteamGames)
        self.steamScanner = None
        self.directoryScanners = []
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
        self.repository.save_window_geometry(self.saveGeometry())

    def readSettings(self):
        """Read window geometry from registry"""
        geometry = self.repository.window_geometry()
        firstRun = False
        if geometry.isEmpty():
            firstRun = True
            self.setGeometry(0, 0, 800, 600)
        else:
            self.restoreGeometry(geometry)
        if firstRun:
            self.logger.info("First run")
            FirstRun(self).showWindow()

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

    def scanSteamGames(self):
        """Discover supported game files in installed Steam games."""
        if self.steamScanner is not None:
            return
        self.steamScanAction.setEnabled(False)
        self.status.showMessage("Finding installed Steam games…")
        self.steamScanner = SteamScanner(self)
        self.steamScanner.progress.connect(self.status.showMessage)
        self.steamScanner.completed.connect(self.steamScanCompleted)
        self.steamScanner.failed.connect(self.steamScanFailed)
        self.steamScanner.finished.connect(self.steamScanFinished)
        self.steamScanner.start()

    def steamScanCompleted(self, installed, found, errors):
        self.gameList.refresh()
        if not installed:
            message = "No installed Steam games found. Use Add Games to choose a folder manually."
        else:
            message = f"Steam scan complete: {found} supported game files found in {installed} installs."
        if errors:
            message += f" {errors} files or folders could not be read."
        self.status.showMessage(message)

    def steamScanFailed(self, error):
        self.gameList.refresh()
        self.status.showMessage(f"Steam scan failed: {error}")

    def steamScanFinished(self):
        self.steamScanner.deleteLater()
        self.steamScanner = None
        self.steamScanAction.setEnabled(True)

    def getRunners(self):
        """Add all compatible source ports to combobox"""
        self.currentRunners.clear()
        self.runnerCombobox.clear()
        record = self.gameList.selected_record
        if record is not None:
            game = record.base if isinstance(record, Modpack) else record.family

            self.game = game
            is_modpack = isinstance(record, Modpack)
            selection_name = record.name
            lastRunner, _ = self.repository.last_selection(selection_name, modpack=is_modpack)
            runners = self.repository.library().compatible_runners(game, preferred=lastRunner)
            self.currentRunners.extend(runner.name for runner in runners)
            self.logger.debug(
                f"Compatible runners for \"{game}\": {self.currentRunners}")
            if len(self.currentRunners) == 0:
                self.runnerCombobox.adjustSize()
                self.runnerCombobox.setEnabled(False)
                self.runnerCombobox.addItem("Add source port")
            else:
                self.runnerCombobox.adjustSize()
                for runner in runners:
                    self.runnerCombobox.addItem(runner.name, runner)

                self.runnerCombobox.setEnabled(True)
        else:
            self.runnerCombobox.adjustSize()
            self.runnerCombobox.setEnabled(False)
            self.runnerCombobox.addItem("Select a game first")

    def getVersions(self):
        """Add all versions of the selected game to combobox"""
        self.currentVersions.clear()
        self.versionCombobox.clear()
        record = self.gameList.selected_record
        if record is not None:
            is_modpack = isinstance(record, Modpack)
            selection_name = record.name
            _, lastVersion = self.repository.last_selection(selection_name, modpack=is_modpack)
            versions = self.repository.library().installed_versions(
                selection_name, modpack=is_modpack, preferred=lastVersion
            )
            self.currentVersions.extend(version.name for version in versions)
            for version in versions:
                label = f"{version.display_name} — {version.path}" if version.path else version.display_name
                self.versionCombobox.addItem(label, version)
            self.versionCombobox.adjustSize()
            self.versionCombobox.setEnabled(bool(versions))
            self.logger.debug(f"\"{selection_name}\" versions: {self.currentVersions}")
        else:
            self.versionCombobox.adjustSize()
            self.versionCombobox.setEnabled(False)
            self.versionCombobox.addItem("Versions")

    def launchGame(self):
        """Launch currently selected game with currently selected source port"""
        runnerList = RunnerView(self)
        version = self.versionCombobox.currentData()
        version_text = version.name if version else ""
        runner = self.runnerCombobox.currentData()
        self.runnerText = runner.name if runner else ""
        self.process = GameLauncher(self)
        self.process.finished.connect(self.clearStatus)
        self.process.finished.connect(self.gameClosed)
        try:
            record = self.gameList.selected_record
            if record is None:
                raise ValueError("Select a game first")
            is_modpack = isinstance(record, Modpack)
            selection_name = record.name
            self.repository.save_selection(
                selection_name, self.runnerText, version_text, modpack=is_modpack)
            version = self.versionCombobox.currentData()
            if version is None:
                raise ValueError("Select an installed game version")
            game = version.path
            if len(self.currentRunners) == 0:
                runnerList.showWindow(self.game)
            else:
                self.originalPath = os.getcwd()
                if is_modpack:
                    self.process.runGame(
                        self.game, game, self.runnerText, [file.path for file in record.files])
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
        if self.steamScanner is not None:
            self.steamScanner.requestInterruption()
            self.steamScanner.wait()
        for worker in self.directoryScanners:
            worker.requestInterruption()
            worker.wait()
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
