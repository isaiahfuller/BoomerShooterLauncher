"""A game launcher for old FPS games"""

from controllers.modpack_controller import ModpackController
import logging
import platform
import sys

import qtawesome as qta
from PySide6 import QtCore, QtGui, QtWidgets

from controllers.library_controller import LibraryController
from controllers.launch_controller import LaunchController
from controllers.scan_controller import ScanController
from controllers.presence_controller import PresenceController
from services.discord import Discord
from views.first_run_view import FirstRun
from views.games_view import GamesView
from views.import_view import ModsImport
from models.records import Modpack
from views.mods_view import ModsView
from repositories.settings_repository import SettingsRepository
from views.runner_view import RunnerView
from views.theme import Theme


class MainWindow(QtWidgets.QMainWindow):
    """Main launcher window"""

    launchRequested = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.status = self.statusBar()
        self.logger = logging.getLogger("Main window")
        if "--debug" in sys.argv:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Debug mode")
        self.platform = platform.system()

        self.theme = Theme(QtWidgets.QApplication.instance().setStyleSheet)

        self.repository = SettingsRepository()
        self.modpackController = ModpackController(self.repository, self)
        self.modpackController.failed.connect(self._show_launch_error)

        self.readSettings()
        self.discord = Discord()
        self.presenceController = PresenceController(self.discord, self)
        self.presenceController.status_changed.connect(self.status.showMessage)

        self.gameList = GamesView(self)
        self.launchController = LaunchController(self.repository, self)
        self.launchRequested.connect(self._request_launch)
        self.launchController.started.connect(self._launch_started)
        self.launchController.stopped.connect(self.clearStatus)
        self.launchController.failed.connect(self._show_launch_error)
        self.launchController.runners_needed.connect(self._open_runner_setup)
        self.game = None
        self.currentRunners = []
        self.currentVersions = []

        iconColor = "grey"
        plusIcon = qta.icon("fa5s.plus", color=iconColor)
        codeIcon = qta.icon("fa5s.code", color=iconColor)
        listIcon = qta.icon("fa5s.list-ol", color=iconColor)
        loadIcon = qta.icon("fa5s.file-download", color=iconColor)
        refreshIcon = qta.icon("fa5s.sync-alt", color=iconColor)

        self.gameList.setHorizontalHeaderLabels(["", "Name", "Files"])

        fileToolbar = self.addToolBar("Toolbar")
        self.addToolBarBreak()
        self.runnerToolbar = self.addToolBar("Launcher")
        fileToolbar.setMovable(False)

        fileToolbar.addAction(codeIcon, "&Manage Ports", self.showRunnerList)
        fileToolbar.addAction(plusIcon, "&Add Games", self.gameScanner)
        self.scanController = ScanController(self.repository, self)
        self.scanController.progress.connect(self.status.showMessage)
        self.scanController.library_changed.connect(self.gameList.refresh)
        self.scanController.manual_finished.connect(
            lambda: self.status.showMessage("Scan complete.")
        )
        self.scanController.steam_completed.connect(self.steamScanCompleted)
        self.scanController.steam_failed.connect(self.steamScanFailed)
        fileToolbar.addAction(listIcon, "&New Modpack", self.showModWindow)
        fileToolbar.addAction(loadIcon, "&Import Modpack", self.importModpack)

        fileToolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        if self.logger.level == logging.DEBUG:
            fileToolbar.addAction(refreshIcon, "&Refresh", self.gameList.refresh)

        self.runnerCombobox = QtWidgets.QComboBox()
        self.runnerCombobox.addItem("Select a game first")
        self.versionCombobox = QtWidgets.QComboBox()
        self.versionCombobox.addItem("Versions")
        self.launchButton = QtWidgets.QPushButton("Launch", self)
        self.runnerCombobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.versionCombobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.runnerCombobox.setEnabled(False)
        self.versionCombobox.setEnabled(False)

        self.runnerToolbar.addWidget(self.runnerCombobox)
        self.runnerToolbar.addWidget(self.versionCombobox)
        self.runnerToolbar.addWidget(self.launchButton)

        self.runnerToolbar.setStyleSheet("QToolBar{spacing: 5px;}")

        self.libraryController = LibraryController(self.repository, self)
        self.libraryController.choices_changed.connect(self._show_library_choices)
        self.gameList.itemSelectionChanged.connect(self._request_library_choices)
        self.gameList.refresh_requested.connect(self.libraryController.refresh)
        self.libraryController.records_changed.connect(self.gameList.render_records)
        self.gameList.add_modpack_requested.connect(self.showModWindow)
        self.gameList.edit_modpack_requested.connect(self.editModpack)
        self.gameList.remove_modpack_requested.connect(self.removeModpack)
        self.libraryController.refresh()

        self.launchButton.clicked.connect(self.launchGame)
        self.gameList.cellActivated.connect(self.launchGame)

        self.presenceController.start()

        self.setCentralWidget(self.gameList)
        self.setAcceptDrops(True)

        self.scanController.scan_steam()

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
        """Choose a directory and submit it to the scan controller."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Add Games")
        if directory:
            self.scanController.scan_paths([directory])

    @property
    def steamScanner(self):
        return self.scanController.steam_worker

    def scanSteamGames(self):
        self.scanController.scan_steam()

    def steamScanCompleted(self, installed, found, errors):
        if not installed:
            message = "No installed Steam games found. Use Add Games to choose a folder manually."
        else:
            message = f"Steam scan complete: {found} supported game files found in {installed} installs."
        if errors:
            message += f" {errors} files or folders could not be read."
        self.status.showMessage(message)

    def steamScanFailed(self, error):
        self.status.showMessage(f"Steam scan failed: {error}")

    def _request_library_choices(self):
        self.libraryController.select(self.gameList.selected_record)

    def getRunners(self):
        """Compatibility entry point for refreshing selection choices."""
        self._request_library_choices()

    def getVersions(self):
        """Compatibility entry point for refreshing selection choices."""
        self._request_library_choices()

    def _show_library_choices(self, record, runners, versions):
        """Render controller-supplied records; labels are presentation only."""
        self.game = (
            record.base if isinstance(record, Modpack) else record.family
        ) if record is not None else None
        self.currentRunners[:] = [runner.name for runner in runners]
        self.currentVersions[:] = [version.name for version in versions]
        self.runnerCombobox.clear()
        for runner in runners:
            self.runnerCombobox.addItem(runner.name, runner)
        if not runners:
            self.runnerCombobox.addItem(
                "Select a game first" if record is None else "Add source port"
            )
        self.runnerCombobox.setEnabled(bool(runners))
        self.runnerCombobox.adjustSize()

        self.versionCombobox.clear()
        for version in versions:
            label = (
                f"{version.display_name} — {version.path}"
                if version.path else version.display_name
            )
            self.versionCombobox.addItem(label, version)
        if record is None:
            self.versionCombobox.addItem("Versions")
        self.versionCombobox.setEnabled(bool(versions))
        self.versionCombobox.adjustSize()

    def launchGame(self):
        """Emit launch intent from the view."""
        self.launchRequested.emit()

    def _request_launch(self):
        self.launchController.launch(
            self.gameList.selected_record,
            self.versionCombobox.currentData(),
            self.runnerCombobox.currentData(),
            has_runners=bool(self.currentRunners),
        )

    def _launch_started(self, title, runner, version):
        self.presenceController.playing(title, runner, version)

    def _show_launch_error(self, message):
        error_window = QtWidgets.QErrorMessage(self)
        error_window.showMessage(message)

    def _open_runner_setup(self, family):
        view = RunnerView(self)
        view.closed.connect(self._request_library_choices)
        view.showWindow(family)

    def showModWindow(self, record=None):
        """Open a draft with explicit inputs and refresh wiring."""
        editor = self._mod_editor()
        if record and not isinstance(record, bool):
            editor.baseSelect.setCurrentText(record.family or "")
        editor.showWindow()

    def _mod_editor(self):
        editor = ModsView(self)
        editor.refresh_requested.connect(self.libraryController.refresh)
        return editor

    def editModpack(self, record):
        self._mod_editor().openFile(record)

    def removeModpack(self, record):
        if self.modpackController.remove(record):
            self.libraryController.refresh()

    def showRunnerList(self):
        """Creates and displays the runner window"""
        runnerList = RunnerView(self)
        runnerList.closed.connect(self._request_library_choices)
        runnerList.showWindowFromMenu()

    def importModpack(self):
        """Choose a JSON file and render the controller's unresolved draft."""
        chooser = QtWidgets.QFileDialog(self)
        chooser.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        chooser.setNameFilter("Modpack JSON (*.json)")
        if chooser.exec():
            pack = self.modpackController.load_json(chooser.selectedFiles()[0])
            if pack is not None:
                importView = ModsImport(self, pack)
                importView.saved.connect(self.libraryController.refresh)
                importView.showWindow()

    def dragEnterEvent(self, event):
        """Filters things dragged into window"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Scans files and folders dropped onto the window as games"""
        self.scanController.scan_paths(
            [url.toLocalFile() for url in event.mimeData().urls()]
        )
        return super().dropEvent(event)

    def clearStatus(self):
        """Compatibility entry point for launch completion."""
        self.presenceController.idle()

    def updateStatus(self):
        self.presenceController.update()

    @property
    def game_running(self):
        return self.presenceController.running

    @property
    def discordState(self):
        return self.presenceController.state

    @property
    def discordDetails(self):
        return self.presenceController.details

    @property
    def discordTimer(self):
        return self.presenceController.timer

    def closeEvent(self, event: QtGui.QCloseEvent):
        """Saves settings before closing"""
        self.scanController.stop()
        self.launchController.stop()
        self.writeSettings()
        self.presenceController.stop()
        return super().closeEvent(event)

